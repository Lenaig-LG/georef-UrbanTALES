# georef-UrbanTALES
Pipeline to process UrbanTALES data and georeference the domains

## Licence

Ce projet est distribué sous licence **GNU Lesser General Public License v3.0 ou ultérieure** (`LGPL-3.0-or-later`).

Le texte complet se trouve dans les fichiers [`COPYING.LESSER`](COPYING.LESSER) et [`COPYING`](COPYING) (la LGPL-3.0 complète la GPL-3.0).

Copyright (C) 2026 Lenaig Le Grognec



## Configuration des chemins

Le dossier de données n'est pas versionné. Par défaut, le code le cherche
dans `../Data` (à côté du dépôt). Pour l'indiquer ailleurs :

    export URBANTALES_DATA=/chemin/vers/Data
    export URBANTALES_OUTPUT=/chemin/vers/Outputs   # optionnel

Lancement : depuis la racine du dépôt, `python pipeline_process.py`.