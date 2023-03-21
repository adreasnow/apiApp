import sqlalchemy as db
import pandas as pd
from enum import Enum
from datetime import datetime, timedelta
from pretty_html_table import build_table


class JobsDB:
    def __init__(self, generate=False) -> None:
        self.engine = db.create_engine('sqlite:////var/www/api/apiApp/jobs.sqlite', echo=True)
        self.connection = self.engine.connect()
        self.metadata = db.MetaData()
        self.table = db.Table('jobs', self.metadata,
                              db.Column('name', db.String(255), primary_key=True),
                              db.Column('status', db.Enum(self._Status)),
                              db.Column('cluster', db.Enum(self._Cluster)),
                              db.Column('datetime', db.DateTime()),
                              )
        if generate:
            self.generate_table()
        return

    def __enter__(self):
        return self

    def __exit__(self, a, b, c) -> None:
        self.connection.close()
        self.engine.dispose()
        return

    class _Status(Enum):
        submitted = 0
        running = 1
        finished = 2
        failed = 3

        def __str__(self):
            if self.value == 0:
                return '<span style="color:blue;">Submitted</span>'
            elif self.value == 1:
                return '<span style="color:orange;">Running</span>'
            elif self.value == 2:
                return '<span style="color:teal;">Finished</span>'
            elif self.value == 3:
                return '<span style="color:red;">Failed</span>'


    class _Cluster(Enum):
        monarch = 0
        m3 = 1
        gadi = 2

        def __str__(self):
            if self.value == 0:
                return '<span style="color:blue;">MonARCH</span>'
            elif self.value == 1:
                return '<span style="color:green;">M3</span>'
            elif self.value == 2:
                return '<span style="color:red;">Gadi</span>'

    def _clusterToEnum(self, cluster: str) -> _Cluster:
        clusterDB = {'monarch': self._Cluster.monarch,
                     'm3': self._Cluster.m3,
                     'gadi': self._Cluster.gadi}
        return clusterDB[cluster.lower()]

    def _statusToEnum(self, status: str) -> _Status:
        statusDB = {'running': self._Status.running,
                    'submitted': self._Status.submitted,
                    'finished': self._Status.finished,
                    'failed': self._Status.failed}
        return statusDB[status.lower()]

    def generate_table(self) -> None:
        self.metadata.create_all(self.engine)
        return

    def drop_table(self) -> None:
        self.metadata.drop_all(self.engine)
        return

    def add_job(self, name, status, cluster) -> None:
        status_in = self._statusToEnum(status)
        cluster_in = self._clusterToEnum(cluster)
        query = self.table.select().where(self.table.columns.name == name)
        output = self.connection.execute(query)
        if output.fetchone() == None:
            update = db.insert(self.table).values(name=name, status=status_in, cluster=cluster_in, datetime=datetime.now())
            out = f'{name} has been added'
        else:
            update = db.update(self.table).values({'status': status_in, 'cluster': cluster_in, 'datetime': datetime.now()}).where(self.table.columns.name == name)
            out = f'{name} has been edited'
        self.connection.execute(update)
        self.connection.commit()
        return out

    def query(self, days: int = 30) -> str:
        query = self.table.select().where(self.table.columns.datetime >= datetime.now()-timedelta(days=days))
        output = self.connection.execute(query)
        results = output.fetchall()
        df = pd.DataFrame(results)
        df.columns = self.table.columns.keys()
        df.sort_values(by='datetime', ascending=False, inplace=True)
        # pd.DataFrame.to_html(df[['name', 'status', 'cluster']], justify='center', index=False, escape=False)
        table = build_table(df[['name', 'status', 'cluster']], 
                            'orange_light', text_align='center', escape=False,
                            conditions={'Running': {'color': 'orange'}})
        center = '<style>#test {width:100%;height:100%;} table {margin: 0 auto; /* or margin: 0 auto 0 auto */}</style>'
        return center + table

