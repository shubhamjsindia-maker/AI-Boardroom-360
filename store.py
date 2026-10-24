"""Small local persistence layer. Scenarios and meeting objects are immutable snapshots."""
import sqlite3,json,datetime
from pathlib import Path
DB=Path(__file__).resolve().parent/'boardroom.sqlite3'
def connect():
    db=sqlite3.connect(DB)
    db.execute('CREATE TABLE IF NOT EXISTS scenarios (id INTEGER PRIMARY KEY AUTOINCREMENT, company TEXT NOT NULL, created_at TEXT NOT NULL, parent_id INTEGER, title TEXT NOT NULL, input_json TEXT NOT NULL, result_json TEXT NOT NULL)')
    db.execute('CREATE TABLE IF NOT EXISTS meetings (id INTEGER PRIMARY KEY AUTOINCREMENT, scenario_id INTEGER NOT NULL, created_at TEXT NOT NULL, mode TEXT NOT NULL, meeting_json TEXT NOT NULL)')
    db.commit();return db

def save_scenario(company,title,inputs,results,parent_id=None):
    with connect() as db:
        cur=db.execute('INSERT INTO scenarios(company,created_at,parent_id,title,input_json,result_json) VALUES(?,?,?,?,?,?)',(company,datetime.datetime.now(datetime.timezone.utc).isoformat(),parent_id,title,json.dumps(inputs),json.dumps(results)))
        return cur.lastrowid

def list_scenarios():
    with connect() as db:return db.execute('SELECT id,company,title,created_at,parent_id FROM scenarios ORDER BY id DESC').fetchall()

def get_scenario(key):
    with connect() as db:r=db.execute('SELECT id,company,title,input_json,result_json,parent_id FROM scenarios WHERE id=?',(key,)).fetchone()
    return {'id':r[0],'company':r[1],'title':r[2],'inputs':json.loads(r[3]),'results':json.loads(r[4]),'parent_id':r[5]} if r else None

def save_meeting(scenario_id,meeting,mode):
    with connect() as db:
        cur=db.execute('INSERT INTO meetings(scenario_id,created_at,mode,meeting_json) VALUES(?,?,?,?)',(scenario_id,datetime.datetime.now(datetime.timezone.utc).isoformat(),mode,json.dumps(meeting)))
        return cur.lastrowid

def list_meetings():
    with connect() as db:return db.execute('SELECT id,scenario_id,created_at,mode FROM meetings ORDER BY id DESC').fetchall()

def get_meeting(key):
    with connect() as db:r=db.execute('SELECT id,scenario_id,mode,meeting_json FROM meetings WHERE id=?',(key,)).fetchone()
    return {'id':r[0],'scenario_id':r[1],'mode':r[2],'meeting':json.loads(r[3])} if r else None


def add_chair_exchange(meeting_id, exchange):
    """Append an immutable chair/director exchange to the meeting's question log.

    The original debate, votes and recommendation remain unchanged.
    """
    with connect() as db:
        row=db.execute('SELECT meeting_json FROM meetings WHERE id=?',(meeting_id,)).fetchone()
        if row is None: raise ValueError('Meeting not found')
        meeting=json.loads(row[0])
        if not meeting.get('complete'): raise ValueError('Cannot question an incomplete meeting')
        meeting.setdefault('chair_exchanges',[]).append({
            **exchange,'asked_at':datetime.datetime.now(datetime.timezone.utc).isoformat()})
        db.execute('UPDATE meetings SET meeting_json=? WHERE id=?',(json.dumps(meeting),meeting_id))
    return meeting
