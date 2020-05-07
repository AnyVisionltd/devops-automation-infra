import pymysql
from contextlib import closing
import numpy as np
import uuid

def fake_poi(number, memsql_pass):
    HOST = "memsql.default.svc.cluster.local"
    PORT = 3306
    USER = "root"
    PASSWORD = memsql_pass
    DATABASE = "reid_db"
    TABLE = 'poi'
    DETECTION_TYPE = 1
    FEATURES_LENGTH = 256
    POI_TO_GENERATE = number
    cnx = pymysql.connect(host=HOST, port=PORT, user=USER, password=PASSWORD, database=DATABASE)
    memsql_poi_query = """INSERT INTO `{DATABASE}`.`{TABLE}` (`poi_id`,`detection_type`,`is_ignored`,`feature_id`,`features`) VALUES {q}"""
    memsql_actions = list()
    for z in range(1, POI_TO_GENERATE + 1):
        features = np.random.rand(FEATURES_LENGTH)
        norm = np.linalg.norm(features)
        features_norm = features / norm
        memsql_actions.append(features_norm.tolist())
        if z % 10000 == 0 or z == POI_TO_GENERATE + 1:
            with closing(cnx.cursor()) as cursor:
                full_q = memsql_poi_query.format(DATABASE=DATABASE, TABLE=TABLE, q=",".join([
                    "('{}',{},{},'{}',json_array_pack('{}'))".format(
                        str(
                            uuid.uuid4()),
                        DETECTION_TYPE,
                        0, str(
                            uuid.uuid4()),
                        c) for c in
                    memsql_actions]))
                cursor.execute(full_q)
                memsql_actions = list()
        cnx.commit()
