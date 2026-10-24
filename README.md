# jarvis-testrepo

Øvingsrepo for Jarvis Dev-agent (RESONVALE). Endringer kommer bare via pull request, og Tom slår dem sammen selv.

## greeter

Et lite Python-prosjekt (Python 3.9+, ingen avhengigheter) med funksjonene `greet`
og `farewell`:

```python
from greeter import farewell, greet

greet("Tom")  # "Hello, Tom!"
farewell("Tom")  # "Ha det, Tom!"
```

Begge fjerner mellomrom rundt navnet, og gir `TypeError` hvis navnet ikke er en
streng, og `ValueError` hvis det er tomt eller lengre enn 100 tegn.

Kjør testene fra rotmappen:

```sh
python -m unittest
```
