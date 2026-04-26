from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import sqlite3
import os
from datetime import datetime

app = Flask(__name__, static_folder=".")
CORS(app)
DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "journal.db")

def get_db():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    return con

def init_db():
    with get_db() as con:
        # Flik 1 - Körjournal
        con.execute("""
            CREATE TABLE IF NOT EXISTS korjournal (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                datum TEXT NOT NULL,
                dag TEXT,
                rutt TEXT,
                amount REAL DEFAULT 0,
                diesel REAL DEFAULT 0,
                driver_income REAL DEFAULT 0,
                remittance REAL DEFAULT 0,
                odo_start REAL,
                odo_stop REAL,
                mil_distance REAL,
                lit_diesel REAL,
                diesel_consumption REAL,
                skapad TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        # Flik 2 - Utgifter
        con.execute("""
            CREATE TABLE IF NOT EXISTS utgifter (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                datum TEXT NOT NULL,
                expensives REAL DEFAULT 0,
                kommentar TEXT,
                skapad TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        # Flik 2 - BDO insättningar
        con.execute("""
            CREATE TABLE IF NOT EXISTS bdo (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                datum TEXT NOT NULL,
                belopp REAL DEFAULT 0,
                skapad TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        # Flik 2 - Lorna insättningar
        con.execute("""
            CREATE TABLE IF NOT EXISTS lorna (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                datum TEXT NOT NULL,
                belopp REAL DEFAULT 0,
                skapad TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

# ── Statiska sidor ──────────────────────────────────────────────
@app.route("/")
def index():
    return send_from_directory(".", "index.html")

@app.route("/utgifter")
def utgifter_sida():
    return send_from_directory(".", "utgifter.html")

@app.route("/summering")
def summering_sida():
    return send_from_directory(".", "summering.html")

# ── Körjournal API ──────────────────────────────────────────────
@app.route("/api/korjournal", methods=["POST"])
def spara_kor():
    d = request.json
    datum = d.get("datum", "")
    dag = ""
    try:
        dt = datetime.strptime(datum, "%Y-%m-%d")
        dagar = ["Mån","Tis","Ons","Tor","Fre","Lör","Sön"]
        dag = dagar[dt.weekday()]
    except:
        pass

    amount = float(d.get("amount") or 0)
    diesel = float(d.get("diesel") or 0)
    odo_start = float(d.get("odo_start") or 0) if d.get("odo_start") else None
    odo_stop = float(d.get("odo_stop") or 0) if d.get("odo_stop") else None
    lit_diesel = float(d.get("lit_diesel") or 0) if d.get("lit_diesel") else None

    # Beräkningar
    driver_income = round(amount * 0.25, 4)
    remittance = round(amount - diesel - driver_income, 4)
    mil_distance = round((odo_stop - odo_start) / 10, 2) if odo_start and odo_stop else None
    diesel_consumption = round(lit_diesel / mil_distance, 6) if lit_diesel and mil_distance and mil_distance > 0 else None

    with get_db() as con:
        con.execute("""
            INSERT INTO korjournal
            (datum, dag, rutt, amount, diesel, driver_income, remittance, odo_start, odo_stop, mil_distance, lit_diesel, diesel_consumption)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
        """, (datum, dag, d.get("rutt",""), amount, diesel, driver_income, remittance,
              odo_start, odo_stop, mil_distance, lit_diesel, diesel_consumption))
    return jsonify({"status": "ok", "meddelande": "Tur sparad"})

@app.route("/api/korjournal", methods=["GET"])
def hamta_kor():
    ar = request.args.get("ar", "")
    with get_db() as con:
        if ar:
            rows = con.execute("SELECT * FROM korjournal WHERE datum LIKE ? ORDER BY datum DESC", (f"{ar}%",)).fetchall()
        else:
            rows = con.execute("SELECT * FROM korjournal ORDER BY datum DESC").fetchall()
    return jsonify([dict(r) for r in rows])

@app.route("/api/korjournal/<int:rid>", methods=["DELETE"])
def ta_bort_kor(rid):
    with get_db() as con:
        con.execute("DELETE FROM korjournal WHERE id=?", (rid,))
    return jsonify({"status": "ok"})

@app.route("/api/korjournal/<int:rid>", methods=["PUT"])
def uppdatera_kor(rid):
    d = request.json
    datum = d.get("datum", "")
    dag = ""
    try:
        dt = datetime.strptime(datum, "%Y-%m-%d")
        dagar = ["Mån","Tis","Ons","Tor","Fre","Lör","Sön"]
        dag = dagar[dt.weekday()]
    except:
        pass
    amount = float(d.get("amount") or 0)
    diesel = float(d.get("diesel") or 0)
    odo_start = float(d.get("odo_start") or 0) if d.get("odo_start") else None
    odo_stop = float(d.get("odo_stop") or 0) if d.get("odo_stop") else None
    lit_diesel = float(d.get("lit_diesel") or 0) if d.get("lit_diesel") else None
    driver_income = round((amount - diesel) * 0.25, 4)
    remittance = round((amount - diesel) * 0.75, 4)
    mil_distance = round((odo_stop - odo_start) / 10, 2) if odo_start and odo_stop else None
    diesel_consumption = round(lit_diesel / mil_distance, 2) if lit_diesel and mil_distance and mil_distance > 0 else None
    with get_db() as con:
        con.execute("""
            UPDATE korjournal SET datum=?, dag=?, rutt=?, amount=?, diesel=?, driver_income=?,
            remittance=?, odo_start=?, odo_stop=?, mil_distance=?, lit_diesel=?, diesel_consumption=?
            WHERE id=?
        """, (datum, dag, d.get("rutt",""), amount, diesel, driver_income, remittance,
              odo_start, odo_stop, mil_distance, lit_diesel, diesel_consumption, rid))
    return jsonify({"status": "ok"})

# ── Utgifter API ────────────────────────────────────────────────
@app.route("/api/utgifter", methods=["POST"])
def spara_utgift():
    d = request.json
    with get_db() as con:
        con.execute("INSERT INTO utgifter (datum, expensives, kommentar) VALUES (?,?,?)",
                    (d.get("datum"), float(d.get("expensives") or 0), d.get("kommentar","")))
    return jsonify({"status": "ok", "meddelande": "Utgift sparad"})

@app.route("/api/utgifter", methods=["GET"])
def hamta_utgifter():
    ar = request.args.get("ar", "")
    with get_db() as con:
        if ar:
            rows = con.execute("SELECT * FROM utgifter WHERE datum LIKE ? ORDER BY datum DESC", (f"{ar}%",)).fetchall()
        else:
            rows = con.execute("SELECT * FROM utgifter ORDER BY datum DESC").fetchall()
    return jsonify([dict(r) for r in rows])

@app.route("/api/utgifter/<int:rid>", methods=["DELETE"])
def ta_bort_utgift(rid):
    with get_db() as con:
        con.execute("DELETE FROM utgifter WHERE id=?", (rid,))
    return jsonify({"status": "ok"})

# ── BDO API ─────────────────────────────────────────────────────
@app.route("/api/bdo", methods=["POST"])
def spara_bdo():
    d = request.json
    with get_db() as con:
        con.execute("INSERT INTO bdo (datum, belopp) VALUES (?,?)",
                    (d.get("datum"), float(d.get("belopp") or 0)))
    return jsonify({"status": "ok", "meddelande": "BDO-insättning sparad"})

@app.route("/api/bdo", methods=["GET"])
def hamta_bdo():
    ar = request.args.get("ar", "")
    with get_db() as con:
        if ar:
            rows = con.execute("SELECT * FROM bdo WHERE datum LIKE ? ORDER BY datum DESC", (f"{ar}%",)).fetchall()
        else:
            rows = con.execute("SELECT * FROM bdo ORDER BY datum DESC").fetchall()
    return jsonify([dict(r) for r in rows])

@app.route("/api/bdo/<int:rid>", methods=["DELETE"])
def ta_bort_bdo(rid):
    with get_db() as con:
        con.execute("DELETE FROM bdo WHERE id=?", (rid,))
    return jsonify({"status": "ok"})

# ── Lorna API ───────────────────────────────────────────────────
@app.route("/api/lorna", methods=["POST"])
def spara_lorna():
    d = request.json
    with get_db() as con:
        con.execute("INSERT INTO lorna (datum, belopp) VALUES (?,?)",
                    (d.get("datum"), float(d.get("belopp") or 0)))
    return jsonify({"status": "ok", "meddelande": "Lorna-insättning sparad"})

@app.route("/api/lorna", methods=["GET"])
def hamta_lorna():
    ar = request.args.get("ar", "")
    with get_db() as con:
        if ar:
            rows = con.execute("SELECT * FROM lorna WHERE datum LIKE ? ORDER BY datum DESC", (f"{ar}%",)).fetchall()
        else:
            rows = con.execute("SELECT * FROM lorna ORDER BY datum DESC").fetchall()
    return jsonify([dict(r) for r in rows])

@app.route("/api/lorna/<int:rid>", methods=["DELETE"])
def ta_bort_lorna(rid):
    with get_db() as con:
        con.execute("DELETE FROM lorna WHERE id=?", (rid,))
    return jsonify({"status": "ok"})

# ── Summering API ───────────────────────────────────────────────
@app.route("/api/summering", methods=["GET"])
def summering():
    with get_db() as con:
        # Hämta alla år
        ar_kor = con.execute("SELECT DISTINCT substr(datum,1,4) as ar FROM korjournal").fetchall()
        ar_utg = con.execute("SELECT DISTINCT substr(datum,1,4) as ar FROM utgifter").fetchall()
        ar_bdo = con.execute("SELECT DISTINCT substr(datum,1,4) as ar FROM bdo").fetchall()
        ar_lor = con.execute("SELECT DISTINCT substr(datum,1,4) as ar FROM lorna").fetchall()

        alla_ar = sorted(set(
            [r["ar"] for r in ar_kor] + [r["ar"] for r in ar_utg] +
            [r["ar"] for r in ar_bdo] + [r["ar"] for r in ar_lor]
        ), reverse=True)

        resultat = []
        for ar in alla_ar:
            kor = con.execute("""
                SELECT
                    COALESCE(SUM(driver_income),0) as driver_salary,
                    COALESCE(SUM(remittance),0) as sum_remittance
                FROM korjournal WHERE datum LIKE ?
            """, (f"{ar}%",)).fetchone()

            utg = con.execute("SELECT COALESCE(SUM(expensives),0) as tot FROM utgifter WHERE datum LIKE ?", (f"{ar}%",)).fetchone()
            bdo = con.execute("SELECT COALESCE(SUM(belopp),0) as tot FROM bdo WHERE datum LIKE ?", (f"{ar}%",)).fetchone()
            lor = con.execute("SELECT COALESCE(SUM(belopp),0) as tot FROM lorna WHERE datum LIKE ?", (f"{ar}%",)).fetchone()

            sum_remittance = round(kor["sum_remittance"], 2)
            expensives = round(utg["tot"], 2)
            net_remittance = round(sum_remittance - expensives, 2)

            resultat.append({
                "ar": ar,
                "driver_salary": round(kor["driver_salary"], 2),
                "sum_remittance": sum_remittance,
                "expensives": expensives,
                "net_remittance": net_remittance,
                "input_bdo": round(bdo["tot"], 2),
                "input_lorna": round(lor["tot"], 2)
            })

    return jsonify(resultat)

@app.route("/api/backup", methods=["GET"])
def backup():
    from flask import send_file
    return send_file(DB, as_attachment=True, download_name="journal_backup.db")


@app.route("/api/rakna-om", methods=["POST"])
def rakna_om():
    """Räknar om driver_income och remittance på alla rader med formeln (amount - diesel) * 0.25 / 0.75"""
    antal = 0
    with get_db() as con:
        rows = con.execute("SELECT id, amount, diesel FROM korjournal").fetchall()
        for r in rows:
            amount = r["amount"] or 0
            diesel = r["diesel"] or 0
            net = amount - diesel
            di = round(net * 0.25, 4)
            rem = round(net * 0.75, 4)
            con.execute("UPDATE korjournal SET driver_income=?, remittance=? WHERE id=?", (di, rem, r["id"]))
            antal += 1
    return jsonify({"status": "ok", "antal": antal})


@app.route("/api/ar", methods=["GET"])
def hamta_ar():
    with get_db() as con:
        rows = con.execute("SELECT DISTINCT substr(datum,1,4) as ar FROM korjournal ORDER BY ar DESC").fetchall()
    return jsonify([r["ar"] for r in rows])

if __name__ == "__main__":
    init_db()
    print("\n✅ Körjournal startar!")
    print("📋 Körjournal:  http://localhost:5000")
    print("💰 Utgifter:    http://localhost:5000/utgifter")
    print("📊 Summering:   http://localhost:5000/summering\n")
    app.run(debug=True, port=5000)
