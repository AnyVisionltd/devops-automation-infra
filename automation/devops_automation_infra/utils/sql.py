


def execute(connection, query):
    with connection.cursor() as c:
        res = c.execute(query)
    connection.commit()
    return res


def fetchall(connection, query):
    with connection.cursor() as c:
        c.execute(query)
        return c.fetchall()


def fetchone(connection, query):
    with connection.cursor() as c:
        c.execute(query)
        return c.fetchone()