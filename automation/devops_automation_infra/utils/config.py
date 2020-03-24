prometheus_connection_config = {
    'host': {
        'k8s': 'prom.anv'
    },
    'port': {
        'compose': 9090,
        'k8s': 80
    },
    'url': {
        'compose': 'http://localhost',
        'k8s': 'http://prom.anv/'
    },
    'auth': 'YWRtaW46UGFzc3cwcmQxMjM='
}