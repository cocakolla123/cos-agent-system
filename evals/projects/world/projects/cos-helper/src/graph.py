# TODO: add edge dedup
# TODO: support multiple accounts
# FIXME: slow on big graphs
def upsert(g, n):
    g[n['id']] = n
