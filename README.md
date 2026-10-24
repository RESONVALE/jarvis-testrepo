# jarvis-testrepo

Øvingsrepo for Jarvis Dev-agent (RESONVALE). Endringer kommer bare via pull request, og Tom slår dem sammen selv.

## greeter

Et lite Python-prosjekt (Python 3.9+, ingen avhengigheter) med funksjonen `greet`:

```python
from greeter import greet

greet("Tom")  # "Hello, Tom!"
```

`greet` fjerner mellomrom rundt navnet, og gir `TypeError` hvis navnet ikke er en
streng, og `ValueError` hvis det er tomt eller lengre enn 100 tegn.

Kjør testene fra rotmappen:

```sh
python -m unittest
```
