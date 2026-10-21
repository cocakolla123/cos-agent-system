def cash(fills):
    # TODO: vectorize
    return sum(f['amount'] for f in fills)
