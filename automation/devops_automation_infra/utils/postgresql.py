from devops_automation_infra.utils import sql


def truncate_all(connection):
    queries = "TRUNCATE TABLE cameras CASCADE;" \
              "TRUNCATE TABLE cameras_2_regions CASCADE;" \
              "TRUNCATE TABLE regions CASCADE;" \
              "TRUNCATE TABLE tracks CASCADE;" \
              "DELETE from camera_groups WHERE \"isDefault\" = False;"

    sql.execute(connection, queries)
    connection.rollback()
    connection.reset()