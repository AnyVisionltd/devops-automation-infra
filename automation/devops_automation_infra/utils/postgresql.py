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


def group_exists_in_pg(connection, group_id):
    response = sql.fetchone(connection,
                            f"SELECT * FROM camera_groups WHERE id = '{group_id}' AND \"isDeleted\" = False")
    print(response)
    return response[0] == group_id


def get_num_of_removed_groups(connection):
    response = sql.fetchone(connection, f"SELECT count(*) FROM camera_groups WHERE \"isDeleted\" = True")
    print(response)
    return response[0]


def get_num_of_removed_streams(connection):
    response = sql.fetchone(connection, f"SELECT count(*) FROM cameras Where \"isDeleted\" = True")
    print(response)
    return response[0]
