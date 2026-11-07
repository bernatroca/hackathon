import numbers


def numero(valor):
    if isinstance(valor, numbers.Real) and not isinstance(valor, bool):
        decimals = 0 if float(valor).is_integer() else 1
        return f'{valor:,.{decimals}f}'.translate(str.maketrans({',': '.', '.': ','}))
    return str(valor)
