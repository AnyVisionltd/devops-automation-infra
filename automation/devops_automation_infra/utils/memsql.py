import logging
import pymysql


def truncate_all(connection):
    logging.debug('Truncating all memsql dbs')
    truncate_commands = fetchall(connection,
                                 f"""select concat('truncate table ', TABLE_SCHEMA, '.', TABLE_NAME) as truncate_command
                                    from information_schema.tables t
                                    where TABLE_SCHEMA not in ('information_schema', 'memsql')
                                    and TABLE_NAME not in ('DATABASECHANGELOG', 'DATABASECHANGELOGLOCK'); """)

    commands = ''.join([f"{command['truncate_command']};" for command in truncate_commands])
    execute(connection=connection, query=commands)
    logging.debug('Done Truncating all memsql dbs')


def execute(connection, query):
    with connection.cursor() as c:
        res = c.execute(query)
    connection.commit()
    return res


def fetchall(connection, query):
    with connection.cursor() as c:
        c.execute(query)
        return c.fetchall()


def get_pipeline_partitions(connection, pipeline):
    query = f"select SOURCE_PARTITION_ID from information_schema.pipelines_cursors WHERE PIPELINE_NAME=\"{pipeline}\""
    result = fetchall(connection, query)
    return [partition['SOURCE_PARTITION_ID'] for partition in result]


def delete_pipeline_partitions(connection, pipeline, *partitions):
    partitions = partitions or get_pipeline_partitions(connection, pipeline)
    if not partitions:
        return
    queries = [f"ALTER PIPELINE {pipeline} DROP PARTITION '{partition}'"
                    for partition in partitions]
    joined = ";".join(queries)
    execute(connection, joined)


def reset_pipeline(connection, pipeline_name):
    import pdb; pdb.set_trace()
    logging.debug(f'Reset pipeline {pipeline_name}')

    try:
        execute(connection, f"stop pipeline {pipeline_name};")
    except pymysql.err.InternalError as e:
        logging.debug('pipeline might be stopped in this case just continue')
        err_code = e.args[0]
        PIPELINE_ALREADY_STOPPED = 1939
        if err_code != PIPELINE_ALREADY_STOPPED:
            raise

    execute(connection, f"alter pipeline {pipeline_name} set offsets earliest;")
    delete_pipeline_partitions(connection, pipeline_name)
    execute(connection, f"start pipeline {pipeline_name};")
