def calc_confidence(ds, holders, sn, ins, tweets):
    c = 50 + min(ds*10,20)
    if holders>200: c+=10
    if sn==0: c+=10
    if ins==0: c+=10
    if tweets>1: c+=10
    return min(int(c),100)