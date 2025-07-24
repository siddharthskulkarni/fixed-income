import numpy as np

def macaulay(bond):
    """
    Calculate the Macaulay duration of a bond.
    
    Parameters:
    bond (Bond): The bond object.
    r (float): The yield to maturity of the bond.
    
    Returns:
    float: The Macaulay duration of the bond.
    """
    assert type(bond).__name__ == 'Bond', "Input must be a Bond object"

    cf = bond._cf
    t = bond._t
    pv_cf = cf / (1 + bond.ytm()) ** t
    mac_dur = np.sum(t * pv_cf) / np.sum(pv_cf)
    return mac_dur

def modified(bond):
    """
    Calculate the Modified duration of a bond.
    
    Parameters:
    bond (Bond): The bond object.
    r (float): The yield to maturity of the bond.
    
    Returns:
    float: The Modified duration of the bond.
    """
    assert type(bond).__name__ == 'Bond', "Input must be a Bond object"

    mod_dur = macaulay(bond) / (1 + bond.ytm())
    return mod_dur

def money(bond):
    """
    Calculate the money duration of a bond.
    
    Parameters:
    bond (Bond): The bond object.
    
    Returns:
    float: The money duration of the bond.
    """
    assert type(bond).__name__ == 'Bond', "Input must be a Bond object"

    money_dur = modified(bond) * bond.P
    return money_dur

def convexity(bond):
    """
    Calculate the convexity of a bond.
    
    Parameters:
    bond (Bond): The bond object.
    
    Returns:
    float: The convexity of the bond.
    """
    assert type(bond).__name__ == 'Bond', "Input must be a Bond object"

    cf = bond._cf
    t = bond._t
    pv_cf = cf / (1 + bond.ytm()) ** t
    conv = np.sum(cf * t * (t + 1) / (1 + bond.ytm()) ** (t + 2)) / np.sum(pv_cf)
    return conv