import numpy as np

def _cashflows_and_ytm(bond, ytm):
    if not hasattr(bond, "cashflows"):
        raise TypeError("bond must provide a cashflows() method")
    t, cf = bond.cashflows()
    y = bond.ytm() if ytm is None else float(ytm)
    return t, cf, y


def macaulay(bond, ytm=None):
    """
    Calculate the Macaulay duration of a bond.
    
    Parameters:
    bond (Bond): The bond object.
    ytm (float | None): If provided, use this yield instead of solving for it.
    
    Returns:
    float: The Macaulay duration of the bond.
    """
    t, cf, y = _cashflows_and_ytm(bond, ytm)
    pv_cf = cf / (1.0 + y) ** t
    price = np.sum(pv_cf)
    mac_dur = np.sum(t * pv_cf) / price
    return mac_dur

def modified(bond, ytm=None):
    """
    Calculate the Modified duration of a bond.
    
    Parameters:
    bond (Bond): The bond object.
    ytm (float | None): If provided, use this yield instead of solving for it.
    
    Returns:
    float: The Modified duration of the bond.
    """
    _, _, y = _cashflows_and_ytm(bond, ytm)
    mod_dur = macaulay(bond, ytm=y) / (1.0 + y)
    return mod_dur

def money(bond, ytm=None):
    """
    Calculate the money duration of a bond.
    
    Parameters:
    bond (Bond): The bond object.
    ytm (float | None): If provided, use this yield instead of solving for it.
    
    Returns:
    float: The money duration of the bond.
    """
    t, cf, y = _cashflows_and_ytm(bond, ytm)
    pv_cf = cf / (1.0 + y) ** t
    price = np.sum(pv_cf)
    money_dur = modified(bond, ytm=y) * price
    return money_dur

def convexity(bond, ytm=None):
    """
    Calculate the convexity of a bond.
    
    Parameters:
    bond (Bond): The bond object.
    ytm (float | None): If provided, use this yield instead of solving for it.
    
    Returns:
    float: The convexity of the bond.
    """
    t, cf, y = _cashflows_and_ytm(bond, ytm)
    pv_cf = cf / (1.0 + y) ** t
    price = np.sum(pv_cf)
    conv = np.sum(cf * t * (t + 1.0) / (1.0 + y) ** (t + 2.0)) / price
    return conv
