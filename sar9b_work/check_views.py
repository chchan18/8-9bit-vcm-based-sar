from virtuoso_bridge import VirtuosoClient

c = VirtuosoClient.from_env()
LIB = "8BIT400MVcmredundancySAR"

for cell in ["TOP_9B_BINARY", "TOP_redun1_ADC"]:
    r = c.execute_skill(f'''
      ddGetObj("{LIB}" "{cell}")~>views~>name
    ''', timeout=10)
    print(f"{cell} views: {r.output}")
