from virtuoso_bridge import VirtuosoClient
from virtuoso_bridge.virtuoso.maestro import close_gui_session, open_gui_session


c = VirtuosoClient.from_env()
s = open_gui_session(c, "8BIT400MVcmredundancySAR", "ADC_redun1_tb", timeout=90)
print("fnx", s)
exprs = [
    'let((w) w=hiGetCurrentWindow() list(w~>windowNum hiGetWindowName(w) sevSession(w)))',
    '''
let((out)
  out=nil
  foreach(w hiGetWindowList()
    out=cons(list(w~>windowNum hiGetWindowName(w) car(errset(sevSession(w)))) out))
  out)
''',
    f'maeGetSetup(?session "{s}")',
]
try:
    for expr in exprs:
        r = c.execute_skill(expr, timeout=20)
        print("EXPR:", expr)
        print("OUT :", r.output)
        print("ERR :", r.errors)
finally:
    close_gui_session(c, s, save=False, timeout=90)
