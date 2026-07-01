from flask import Flask, request, jsonify
from flask_cors import CORS
import hashlib, hmac, json, os
from db import *

app = Flask(__name__)
CORS(app)
BOT_TOKEN = os.environ.get("BOT_TOKEN","")
ADMIN_ID = os.environ.get("ADMIN_ID","8030373785")

def verify(init_data):
    try:
        p={}
        for x in init_data.split("&"):
            k,v=x.split("=",1); p[k]=v
        h=p.pop("hash","")
        dc="\n".join(f"{k}={v}" for k,v in sorted(p.items()))
        s=hmac.new(b"WebAppData",BOT_TOKEN.encode(),hashlib.sha256).digest()
        c=hmac.new(s,dc.encode(),hashlib.sha256).hexdigest()
        if hmac.compare_digest(c,h):
            import urllib.parse
            return json.loads(urllib.parse.unquote(p.get("user","{}")))
    except: pass
    return None

def tg(req):
    d=req.headers.get("X-Init-Data","")
    if not d: return None
    return verify(d)

def dev(data):
    return {"id":data.get("telegram_id",0),"username":"dev","first_name":"Dev"}

@app.route("/api/auth",methods=["POST"])
def auth():
    data=request.json or {}
    u=tg(request)
    if not u and os.environ.get("DEV_MODE"): u=dev(data)
    if not u: return jsonify({"error":"Unauthorized"}),401
    tid=str(u["id"])
    user=get_user(tid)
    if not user: user=create_user(tid,u.get("username",""),u.get("first_name",""),data.get("ref"))
    ac,al=airdrop_status()
    return jsonify({"id":tid,"username":u.get("username"),"first_name":u.get("first_name"),"referral_code":user["referral_code"],"ton_balance":user["ton_balance"],"ton_earned":user["ton_earned"],"level":user["level"],"xp":user["xp"],"ref_count":user["ref_count"],"ref_claimed":user["ref_claimed"],"is_admin":tid==ADMIN_ID,"airdrop_available":ac<al})

@app.route("/api/map")
def map_data():
    return jsonify({"lands":get_map_data()})

@app.route("/api/land/<int:x>/<int:y>")
def land_info(x,y):
    l=get_land(x,y)
    if not l: return jsonify({"error":"Not found"}),404
    return jsonify(dict(l))

@app.route("/api/buy",methods=["POST"])
def buy():
    data=request.json or {}; u=tg(request)
    if not u and os.environ.get("DEV_MODE"): u=dev(data)
    if not u: return jsonify({"error":"Unauthorized"}),401
    ok,msg=buy_land(data.get("x"),data.get("y"),str(u["id"]),data.get("tx",""))
    return jsonify({"success":ok,"message":msg}) if ok else (jsonify({"error":msg}),400)

@app.route("/api/secondary_buy",methods=["POST"])
def sec():
    data=request.json or {}; u=tg(request)
    if not u and os.environ.get("DEV_MODE"): u=dev(data)
    if not u: return jsonify({"error":"Unauthorized"}),401
    ok,msg=secondary_buy(data.get("x"),data.get("y"),str(u["id"]),data.get("tx",""))
    return jsonify({"success":ok,"message":msg}) if ok else (jsonify({"error":msg}),400)

@app.route("/api/sell",methods=["POST"])
def sell():
    data=request.json or {}; u=tg(request)
    if not u and os.environ.get("DEV_MODE"): u=dev(data)
    if not u: return jsonify({"error":"Unauthorized"}),401
    set_sale(data.get("x"),data.get("y"),str(u["id"]),data.get("price",1.5))
    return jsonify({"success":True})

@app.route("/api/rent",methods=["POST"])
def rent():
    data=request.json or {}; u=tg(request)
    if not u and os.environ.get("DEV_MODE"): u=dev(data)
    if not u: return jsonify({"error":"Unauthorized"}),401
    set_rent(data.get("x"),data.get("y"),str(u["id"]),data.get("price",0.1))
    return jsonify({"success":True})

@app.route("/api/land/update",methods=["POST"])
def land_upd():
    data=request.json or {}; u=tg(request)
    if not u and os.environ.get("DEV_MODE"): u=dev(data)
    if not u: return jsonify({"error":"Unauthorized"}),401
    kw={k:data[k] for k in ["building","effect","image_url","land_name","land_desc"] if k in data}
    update_land(data.get("x"),data.get("y"),str(u["id"]),**kw)
    return jsonify({"success":True})

@app.route("/api/visit",methods=["POST"])
def visit():
    data=request.json or {}; u=tg(request)
    if not u and os.environ.get("DEV_MODE"): u=dev(data)
    if not u: return jsonify({"error":"Unauthorized"}),401
    visit_land(data.get("x"),data.get("y"),str(u["id"]))
    return jsonify({"success":True})

@app.route("/api/airdrop",methods=["POST"])
def airdrop():
    data=request.json or {}; u=tg(request)
    if not u and os.environ.get("DEV_MODE"): u=dev(data)
    if not u: return jsonify({"error":"Unauthorized"}),401
    ok,msg=claim_airdrop(str(u["id"]))
    return jsonify({"success":ok,"message":msg})

@app.route("/api/profile")
def profile():
    u=tg(request)
    if not u and os.environ.get("DEV_MODE"): u={"id":request.args.get("id",0)}
    if not u: return jsonify({"error":"Unauthorized"}),401
    uid=str(u["id"]); user=get_user(uid); lands=get_user_lands(uid)
    return jsonify({"user":dict(user) if user else {},"lands":[dict(l) for l in lands],"land_count":len(lands)})

@app.route("/api/leaderboard")
def lb():
    return jsonify({"data":get_leaderboard(request.args.get("type","lands"))})

@app.route("/api/stats")
def stats():
    return jsonify(get_stats())

@app.route("/api/market")
def market():
    s,r=get_market()
    return jsonify({"for_sale":s,"for_rent":r})

@app.route("/api/admin/stats")
def adm_stats():
    u=tg(request)
    if not u and os.environ.get("DEV_MODE"): u={"id":ADMIN_ID}
    if not u or str(u["id"])!=ADMIN_ID: return jsonify({"error":"Forbidden"}),403
    return jsonify(get_stats())

@app.route("/api/admin/users")
def adm_users():
    u=tg(request)
    if not u and os.environ.get("DEV_MODE"): u={"id":ADMIN_ID}
    if not u or str(u["id"])!=ADMIN_ID: return jsonify({"error":"Forbidden"}),403
    return jsonify({"users":get_users()})

@app.route("/api/admin/send",methods=["POST"])
def adm_send():
    u=tg(request); data=request.json or {}
    if not u and os.environ.get("DEV_MODE"): u={"id":ADMIN_ID}
    if not u or str(u["id"])!=ADMIN_ID: return jsonify({"error":"Forbidden"}),403
    admin_send(str(data.get("to_id")),float(data.get("amount",0)),data.get("note",""))
    return jsonify({"success":True})

@app.route("/health")
def health():
    return jsonify({"status":"ok","project":"NOVA LAND"})

if __name__=="__main__":
    init_db()
    app.run(host="0.0.0.0",port=int(os.environ.get("PORT",5000)))
