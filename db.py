import sqlite3, os, random, string, json

DB_PATH = os.environ.get("DB_PATH", "/tmp/novaland.db")
ADMIN_ID = os.environ.get("ADMIN_ID", "8030373785")
ADMIN_WALLET = "UQDkd2lpeHyxPD3ag8BuhurdahzxWWeEZpmtWhyYWSClcgFE"
COMMISSION = 0.10
AIRDROP_LIMIT = 100
REF_THRESHOLD = 10

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db(); c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        telegram_id TEXT UNIQUE NOT NULL,
        username TEXT, first_name TEXT,
        referral_code TEXT UNIQUE,
        referred_by TEXT,
        ton_balance REAL DEFAULT 0,
        ton_earned REAL DEFAULT 0,
        ref_count INTEGER DEFAULT 0,
        ref_claimed INTEGER DEFAULT 0,
        level INTEGER DEFAULT 1,
        xp INTEGER DEFAULT 0,
        joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
    c.execute("""CREATE TABLE IF NOT EXISTS lands (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        x INTEGER NOT NULL, y INTEGER NOT NULL,
        owner_id TEXT DEFAULT NULL,
        price REAL DEFAULT 1.0,
        zone TEXT DEFAULT 'suburb',
        is_for_sale INTEGER DEFAULT 0,
        sale_price REAL DEFAULT 0,
        is_for_rent INTEGER DEFAULT 0,
        rent_price REAL DEFAULT 0,
        building TEXT DEFAULT NULL,
        effect TEXT DEFAULT NULL,
        image_url TEXT DEFAULT NULL,
        land_name TEXT DEFAULT NULL,
        land_desc TEXT DEFAULT NULL,
        visits INTEGER DEFAULT 0,
        income REAL DEFAULT 0,
        is_admin INTEGER DEFAULT 0,
        decorations TEXT DEFAULT '[]',
        bg_color TEXT DEFAULT '#001200',
        theme TEXT DEFAULT 'default',
        purchased_at TIMESTAMP DEFAULT NULL,
        UNIQUE(x, y))""")
    c.execute("""CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        type TEXT NOT NULL,
        land_x INTEGER, land_y INTEGER,
        from_user TEXT, to_user TEXT,
        amount REAL NOT NULL,
        commission REAL DEFAULT 0,
        tx_hash TEXT, note TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
    c.execute("""CREATE TABLE IF NOT EXISTS airdrops (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        telegram_id TEXT UNIQUE NOT NULL,
        land_x INTEGER, land_y INTEGER,
        claimed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
    c.execute("""CREATE TABLE IF NOT EXISTS offers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        land_x INTEGER NOT NULL, land_y INTEGER NOT NULL,
        from_user TEXT NOT NULL, to_user TEXT NOT NULL,
        amount REAL NOT NULL,
        status TEXT DEFAULT 'pending',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        responded_at TIMESTAMP DEFAULT NULL)""")
    # migration for older DBs that already exist without new columns
    for col, definition in [("decorations","TEXT DEFAULT '[]'"),("bg_color","TEXT DEFAULT '#001200'"),("theme","TEXT DEFAULT 'default'")]:
        try: c.execute(f"ALTER TABLE lands ADD COLUMN {col} {definition}")
        except: pass
    for x in range(50):
        for y in range(50):
            dist = max(abs(x-24), abs(y-24))
            if x==24 and y==24: zone,price,adm='admin',0,1
            elif dist<=2: zone,price,adm='center',10.0,0
            elif dist<=5: zone,price,adm='downtown',5.0,0
            elif dist<=10: zone,price,adm='midtown',2.0,0
            elif dist<=18: zone,price,adm='suburb',1.0,0
            else: zone,price,adm='outskirts',0.5,0
            try: c.execute("INSERT INTO lands (x,y,price,zone,is_admin) VALUES (?,?,?,?,?)",(x,y,price,zone,adm))
            except: pass
    try: conn.execute("UPDATE lands SET owner_id=?,purchased_at=CURRENT_TIMESTAMP WHERE zone='admin'",(ADMIN_ID,))
    except: pass
    conn.commit(); conn.close(); print("✅ NOVA LAND DB Ready")

def get_user(tid):
    conn=get_db(); u=conn.execute("SELECT * FROM users WHERE telegram_id=?",(str(tid),)).fetchone(); conn.close(); return u

def create_user(tid, username, first_name, ref=None):
    code=''.join(random.choices(string.ascii_uppercase+string.digits,k=8))
    conn=get_db()
    try:
        conn.execute("INSERT INTO users (telegram_id,username,first_name,referral_code,referred_by) VALUES (?,?,?,?,?)",(str(tid),username,first_name,code,ref))
        conn.commit()
        if ref:
            conn.execute("UPDATE users SET ref_count=ref_count+1 WHERE referral_code=?",(ref,)); conn.commit()
            _ref_reward(ref,conn)
    except: pass
    u=conn.execute("SELECT * FROM users WHERE telegram_id=?",(str(tid),)).fetchone(); conn.close(); return u

def _ref_reward(code,conn):
    u=conn.execute("SELECT * FROM users WHERE referral_code=?",(code,)).fetchone()
    if not u: return
    if u['ref_count']//REF_THRESHOLD > u['ref_claimed']:
        free=conn.execute("SELECT * FROM lands WHERE owner_id IS NULL AND zone='suburb' LIMIT 1").fetchone()
        if free: conn.execute("UPDATE lands SET owner_id=?,purchased_at=CURRENT_TIMESTAMP WHERE x=? AND y=?",(u['telegram_id'],free['x'],free['y']))
        else: conn.execute("UPDATE users SET ton_balance=ton_balance+1 WHERE referral_code=?",(code,))
        conn.execute("UPDATE users SET ref_claimed=ref_claimed+1 WHERE referral_code=?",(code,)); conn.commit()

def add_balance(tid,amount,conn=None):
    close=conn is None
    if close: conn=get_db()
    conn.execute("UPDATE users SET ton_balance=ton_balance+?,ton_earned=ton_earned+? WHERE telegram_id=?",(amount,amount,str(tid)))
    if close: conn.commit(); conn.close()

def add_xp(tid,xp,conn=None):
    close=conn is None
    if close: conn=get_db()
    conn.execute("UPDATE users SET xp=xp+? WHERE telegram_id=?",(xp,str(tid)))
    u=conn.execute("SELECT xp FROM users WHERE telegram_id=?",(str(tid),)).fetchone()
    if u: conn.execute("UPDATE users SET level=? WHERE telegram_id=?",(max(1,u['xp']//100+1),str(tid)))
    if close: conn.commit(); conn.close()

def get_land(x,y):
    conn=get_db(); l=conn.execute("SELECT * FROM lands WHERE x=? AND y=?",(x,y)).fetchone(); conn.close(); return l

def get_user_lands(tid):
    conn=get_db(); ls=conn.execute("SELECT * FROM lands WHERE owner_id=? ORDER BY purchased_at DESC",(str(tid),)).fetchall(); conn.close(); return ls

def get_map_data():
    conn=get_db()
    ls=conn.execute("SELECT x,y,owner_id,price,zone,is_for_sale,sale_price,is_for_rent,rent_price,building,effect,image_url,land_name,visits,income,is_admin,bg_color,theme FROM lands").fetchall()
    conn.close(); return [dict(l) for l in ls]

def buy_land(x,y,tid,tx=""):
    conn=get_db()
    l=conn.execute("SELECT * FROM lands WHERE x=? AND y=?",(x,y)).fetchone()
    if not l: conn.close(); return False,"زمین پیدا نشد"
    if l['owner_id']: conn.close(); return False,"خریداری شده"
    if l['is_admin']: conn.close(); return False,"زمین ادمینه"
    amt=l['price']; comm=round(amt*COMMISSION,4)
    conn.execute("UPDATE lands SET owner_id=?,purchased_at=CURRENT_TIMESTAMP WHERE x=? AND y=?",(str(tid),x,y))
    conn.execute("INSERT INTO transactions (type,land_x,land_y,to_user,amount,commission,tx_hash) VALUES ('buy',?,?,?,?,?,?)",(x,y,str(tid),amt,comm,tx))
    add_xp(tid,50,conn); conn.commit(); conn.close(); return True,"✅ زمین خریداری شد"

def secondary_buy(x,y,buyer,tx=""):
    conn=get_db()
    l=conn.execute("SELECT * FROM lands WHERE x=? AND y=?",(x,y)).fetchone()
    if not l or not l['is_for_sale']: conn.close(); return False,"برای فروش نیست"
    amt=l['sale_price']; comm=round(amt*COMMISSION,4); seller_gets=round(amt-comm,4)
    add_balance(l['owner_id'],seller_gets,conn)
    conn.execute("UPDATE lands SET owner_id=?,is_for_sale=0,sale_price=0,purchased_at=CURRENT_TIMESTAMP WHERE x=? AND y=?",(str(buyer),x,y))
    conn.execute("INSERT INTO transactions (type,land_x,land_y,from_user,to_user,amount,commission,tx_hash) VALUES ('secondary',?,?,?,?,?,?,?)",(x,y,l['owner_id'],str(buyer),amt,comm,tx))
    add_xp(buyer,30,conn); conn.commit(); conn.close(); return True,"✅ خرید انجام شد"

def set_sale(x,y,tid,price):
    conn=get_db(); conn.execute("UPDATE lands SET is_for_sale=1,sale_price=? WHERE x=? AND y=? AND owner_id=?",(price,x,y,str(tid))); conn.commit(); conn.close()

def set_rent(x,y,tid,price):
    conn=get_db(); conn.execute("UPDATE lands SET is_for_rent=1,rent_price=? WHERE x=? AND y=? AND owner_id=?",(price,x,y,str(tid))); conn.commit(); conn.close()

def update_land(x,y,tid,**kw):
    conn=get_db(); ok=['building','effect','image_url','land_name','land_desc']; sets=[]; vals=[]
    for k,v in kw.items():
        if k in ok: sets.append(f"{k}=?"); vals.append(v)
    if sets: vals+=[x,y,str(tid)]; conn.execute(f"UPDATE lands SET {','.join(sets)} WHERE x=? AND y=? AND owner_id=?",vals); conn.commit()
    conn.close()

def save_decorations(x,y,tid,decorations,bg_color=None,theme=None):
    """decorations: list of dicts like {type,x,z,rot} -> stored as JSON (position updates / removals, no new paid items)"""
    conn=get_db()
    l=conn.execute("SELECT owner_id FROM lands WHERE x=? AND y=?",(x,y)).fetchone()
    if not l or l['owner_id']!=str(tid): conn.close(); return False,"این زمین مال تو نیست"
    dec_json=json.dumps(decorations, ensure_ascii=False)
    sets=["decorations=?"]; vals=[dec_json]
    if bg_color: sets.append("bg_color=?"); vals.append(bg_color)
    if theme: sets.append("theme=?"); vals.append(theme)
    vals+=[x,y,str(tid)]
    conn.execute(f"UPDATE lands SET {','.join(sets)} WHERE x=? AND y=? AND owner_id=?",vals)
    conn.commit(); conn.close(); return True,"✅ ذخیره شد"

ITEM_CATALOG = {
    "tree":      {"name":"درخت",      "price":0.03},
    "bush":      {"name":"بوته",      "price":0.02},
    "fence":     {"name":"حصار",      "price":0.02},
    "lamp":      {"name":"چراغ",      "price":0.03},
    "well":      {"name":"چاه آب",    "price":0.06},
    "pond":      {"name":"استخر",     "price":0.10},
    "wall":      {"name":"دیوار",     "price":0.02},
    "house_small":{"name":"خانه کوچک","price":0.40},
    "house_big": {"name":"خانه بزرگ", "price":0.90},
    "tower":     {"name":"برج",       "price":0.70},
    "shop_bldg": {"name":"مغازه",     "price":0.60},
    "flower":    {"name":"باغچه گل",  "price":0.02},
}

def buy_item(x,y,tid,item_type):
    if item_type not in ITEM_CATALOG: return False,"آیتم نامعتبر",None
    price=ITEM_CATALOG[item_type]["price"]
    conn=get_db()
    l=conn.execute("SELECT * FROM lands WHERE x=? AND y=?",(x,y)).fetchone()
    if not l or l['owner_id']!=str(tid): conn.close(); return False,"این زمین مال تو نیست",None
    u=conn.execute("SELECT ton_balance FROM users WHERE telegram_id=?",(str(tid),)).fetchone()
    if not u or u['ton_balance']<price: conn.close(); return False,"موجودی TON کافی نیست",None
    try: decs=json.loads(l['decorations'] or '[]')
    except: decs=[]
    import random as _r
    new_item={"type":item_type,"x":round(_r.uniform(-3,3),2),"z":round(_r.uniform(-3,3),2),"rot":0}
    decs.append(new_item)
    conn.execute("UPDATE users SET ton_balance=ton_balance-? WHERE telegram_id=?",(price,str(tid)))
    conn.execute("UPDATE lands SET decorations=? WHERE x=? AND y=?",(json.dumps(decs,ensure_ascii=False),x,y))
    conn.execute("INSERT INTO transactions (type,land_x,land_y,from_user,amount,note) VALUES ('shop_item',?,?,?,?,?)",(x,y,str(tid),price,item_type))
    conn.commit(); conn.close()
    return True,"✅ خریداری شد",decs

def get_land_full(x,y):
    conn=get_db(); l=conn.execute("SELECT * FROM lands WHERE x=? AND y=?",(x,y)).fetchone(); conn.close()
    if not l: return None
    d=dict(l)
    try: d['decorations']=json.loads(d.get('decorations') or '[]')
    except: d['decorations']=[]
    return d

def visit_land(x,y,tid):
    conn=get_db()
    conn.execute("UPDATE lands SET visits=visits+1 WHERE x=? AND y=?",(x,y))
    l=conn.execute("SELECT * FROM lands WHERE x=? AND y=?",(x,y)).fetchone()
    if l and l['owner_id'] and l['visits']%1000==0:
        add_balance(l['owner_id'],0.01,conn)
        conn.execute("UPDATE lands SET income=income+0.01 WHERE x=? AND y=?",(x,y))
        conn.execute("INSERT INTO transactions (type,land_x,land_y,to_user,amount,note) VALUES ('visit',?,?,?,0.01,'1000 بازدید')",(x,y,l['owner_id']))
    conn.commit(); conn.close()

def claim_airdrop(tid):
    conn=get_db()
    cnt=conn.execute("SELECT COUNT(*) FROM airdrops").fetchone()[0]
    if cnt>=AIRDROP_LIMIT: conn.close(); return False,"ایردراپ تموم شد"
    if conn.execute("SELECT * FROM airdrops WHERE telegram_id=?",(str(tid),)).fetchone(): conn.close(); return False,"قبلاً گرفتی"
    free=conn.execute("SELECT * FROM lands WHERE owner_id IS NULL AND zone='outskirts' LIMIT 1").fetchone()
    if not free: free=conn.execute("SELECT * FROM lands WHERE owner_id IS NULL AND zone='suburb' LIMIT 1").fetchone()
    if not free: conn.close(); return False,"زمین موجود نیست"
    conn.execute("UPDATE lands SET owner_id=?,purchased_at=CURRENT_TIMESTAMP WHERE x=? AND y=?",(str(tid),free['x'],free['y']))
    conn.execute("INSERT INTO airdrops (telegram_id,land_x,land_y) VALUES (?,?,?)",(str(tid),free['x'],free['y']))
    conn.commit(); rem=AIRDROP_LIMIT-cnt-1; conn.close()
    return True,f"🎁 زمین ({free['x']},{free['y']}) مال توئه! {rem} تا مونده"

def airdrop_status():
    conn=get_db(); cnt=conn.execute("SELECT COUNT(*) FROM airdrops").fetchone()[0]; conn.close(); return cnt,AIRDROP_LIMIT

def get_leaderboard(type='lands'):
    conn=get_db()
    if type=='lands': rows=conn.execute("SELECT u.telegram_id,u.username,u.first_name,u.level,COUNT(l.id) as score FROM users u LEFT JOIN lands l ON l.owner_id=u.telegram_id GROUP BY u.telegram_id ORDER BY score DESC LIMIT 20").fetchall()
    elif type=='income': rows=conn.execute("SELECT telegram_id,username,first_name,level,ton_earned as score FROM users ORDER BY ton_earned DESC LIMIT 20").fetchall()
    elif type=='visits': rows=conn.execute("SELECT u.telegram_id,u.username,u.first_name,u.level,COALESCE(SUM(l.visits),0) as score FROM users u LEFT JOIN lands l ON l.owner_id=u.telegram_id GROUP BY u.telegram_id ORDER BY score DESC LIMIT 20").fetchall()
    else: rows=[]
    conn.close(); return [dict(r) for r in rows]

def get_stats():
    conn=get_db()
    r=lambda q: conn.execute(q).fetchone()[0]
    d={"total_lands":r("SELECT COUNT(*) FROM lands WHERE is_admin=0"),"sold_lands":r("SELECT COUNT(*) FROM lands WHERE owner_id IS NOT NULL AND is_admin=0"),"total_users":r("SELECT COUNT(*) FROM users"),"total_volume":round(r("SELECT COALESCE(SUM(amount),0) FROM transactions"),2),"total_commission":round(r("SELECT COALESCE(SUM(commission),0) FROM transactions"),2),"airdrop_count":r("SELECT COUNT(*) FROM airdrops")}
    d["available"]=d["total_lands"]-d["sold_lands"]; d["airdrop_left"]=AIRDROP_LIMIT-d["airdrop_count"]
    conn.close(); return d

def admin_send(to,amount,note=""):
    conn=get_db(); add_balance(to,amount,conn)
    conn.execute("INSERT INTO transactions (type,from_user,to_user,amount,note) VALUES ('admin',?,?,?,?)",(ADMIN_ID,str(to),amount,note))
    conn.commit(); conn.close()

def get_users():
    conn=get_db()
    us=conn.execute("SELECT u.*,COUNT(l.id) as lc FROM users u LEFT JOIN lands l ON l.owner_id=u.telegram_id GROUP BY u.telegram_id ORDER BY u.joined_at DESC").fetchall()
    conn.close(); return [dict(u) for u in us]

def get_market():
    conn=get_db()
    s=conn.execute("SELECT l.*,u.username,u.first_name FROM lands l LEFT JOIN users u ON u.telegram_id=l.owner_id WHERE l.is_for_sale=1 ORDER BY l.sale_price ASC LIMIT 20").fetchall()
    r=conn.execute("SELECT l.*,u.username,u.first_name FROM lands l LEFT JOIN users u ON u.telegram_id=l.owner_id WHERE l.is_for_rent=1 ORDER BY l.rent_price ASC LIMIT 20").fetchall()
    conn.close(); return [dict(x) for x in s],[dict(x) for x in r]

# ---------- Offers (پیشنهاد قیمت) ----------

def make_offer(x,y,from_tid,amount):
    conn=get_db()
    l=conn.execute("SELECT * FROM lands WHERE x=? AND y=?",(x,y)).fetchone()
    if not l: conn.close(); return False,"زمین پیدا نشد"
    if not l['owner_id']: conn.close(); return False,"این زمین صاحب نداره، مستقیم بخرش"
    if l['owner_id']==str(from_tid): conn.close(); return False,"این زمین خودته"
    if l['is_admin']: conn.close(); return False,"زمین ادمینه"
    existing=conn.execute("SELECT id FROM offers WHERE land_x=? AND land_y=? AND from_user=? AND status='pending'",(x,y,str(from_tid))).fetchone()
    if existing:
        conn.execute("UPDATE offers SET amount=?,created_at=CURRENT_TIMESTAMP WHERE id=?",(amount,existing['id']))
    else:
        conn.execute("INSERT INTO offers (land_x,land_y,from_user,to_user,amount) VALUES (?,?,?,?,?)",(x,y,str(from_tid),l['owner_id'],amount))
    conn.commit(); conn.close(); return True,"✅ پیشنهادت ثبت شد"

def get_land_offers(x,y,owner_tid):
    conn=get_db()
    rows=conn.execute("""SELECT o.*,u.first_name,u.username FROM offers o LEFT JOIN users u ON u.telegram_id=o.from_user
        WHERE o.land_x=? AND o.land_y=? AND o.to_user=? AND o.status='pending' ORDER BY o.amount DESC""",(x,y,str(owner_tid))).fetchall()
    conn.close(); return [dict(r) for r in rows]

def get_my_offers(tid):
    conn=get_db()
    sent=conn.execute("SELECT * FROM offers WHERE from_user=? ORDER BY created_at DESC LIMIT 30",(str(tid),)).fetchall()
    received=conn.execute("SELECT * FROM offers WHERE to_user=? AND status='pending' ORDER BY amount DESC LIMIT 30",(str(tid),)).fetchall()
    conn.close(); return [dict(r) for r in sent],[dict(r) for r in received]

def respond_offer(offer_id,tid,action):
    conn=get_db()
    o=conn.execute("SELECT * FROM offers WHERE id=?",(offer_id,)).fetchone()
    if not o: conn.close(); return False,"پیشنهاد پیدا نشد"
    if o['to_user']!=str(tid): conn.close(); return False,"این پیشنهاد مال تو نیست"
    if o['status']!='pending': conn.close(); return False,"قبلاً پاسخ داده شده"
    if action=='reject':
        conn.execute("UPDATE offers SET status='rejected',responded_at=CURRENT_TIMESTAMP WHERE id=?",(offer_id,))
        conn.commit(); conn.close(); return True,"❌ پیشنهاد رد شد"
    if action=='accept':
        amt=o['amount']; comm=round(amt*COMMISSION,4); seller_gets=round(amt-comm,4)
        add_balance(o['to_user'],seller_gets,conn)
        conn.execute("UPDATE lands SET owner_id=?,is_for_sale=0,sale_price=0,purchased_at=CURRENT_TIMESTAMP WHERE x=? AND y=?",(o['from_user'],o['land_x'],o['land_y']))
        conn.execute("INSERT INTO transactions (type,land_x,land_y,from_user,to_user,amount,commission,note) VALUES ('offer',?,?,?,?,?,?,'پیشنهاد قبول شد')",(o['land_x'],o['land_y'],o['to_user'],o['from_user'],amt,comm))
        conn.execute("UPDATE offers SET status='accepted',responded_at=CURRENT_TIMESTAMP WHERE id=?",(offer_id,))
        conn.execute("UPDATE offers SET status='rejected',responded_at=CURRENT_TIMESTAMP WHERE land_x=? AND land_y=? AND id!=? AND status='pending'",(o['land_x'],o['land_y'],offer_id))
        add_xp(o['from_user'],30,conn)
        conn.commit(); conn.close(); return True,"✅ پیشنهاد قبول شد، زمین منتقل شد"
    conn.close(); return False,"دستور نامعتبر"
