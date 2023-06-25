from .db_handler import JobsDB
from flask import Flask
import os

app = Flask(__name__)
if not os.path.exists('/var/www/api/apiApp/jobs.sqlite'):
    JobsDB(generate=True)

@app.route('/id/<string:job_ID>/<string:status>/<string:cluster>/', methods=['GET', 'POST'])
def id(job_ID: str, status: str, cluster: str) -> str:
    with JobsDB() as jobsDB:
        out = jobsDB.add_job(job_ID, status, cluster)
    return out

@app.route('/db/', defaults={'days': 30, 'search': '-'})
@app.route('/db/<search>/', defaults={'days': 30})
@app.route('/db/<search>/<int:days>/')
def db(days: int, search: str) -> str:
    with JobsDB() as jobsDB:
        out = jobsDB.query(days=days, search=search)
    return out

if __name__ == '__main__':
    app.run()
