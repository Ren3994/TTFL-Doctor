# 🏀 TTFL Doctor 

Application python pour aider à faire des choix sur la TrashTalk Fantasy League (TTFL) : https://fantasy.trashtalk.co

Disclaimer : Ce projet est 100% personnel réalisé dans le but d'apprendre des techniques et de faire des best picks mais n'est pas affilié à l'équipe de TrashTalk.

## Pages disponibles : 

### 1. Classement TTFL du jour 
Donne le classement des joueurs TTFL jouant ce soir avec des informations sur les blessures et les stats TTFL.

<img width="1336" height="994" alt="Classement" src="https://github.com/user-attachments/assets/61937031-4c11-48d3-8ee2-c877bec24cf5" /><br><br>

Cliquer sur les flèches à droite et à gauche de la date, ou simplement rentrer une nouvelle date dans la case permet de naviguer entre les différentes journées de matchs.

Survoler certaines colonnes des joueurs fait apparaître des statistiques plus avancées (graphes des évolution des scores, stats par poste, maison/extérieur, influence des blessures des coéquipiers et des adversaires, ...). Par exemple :

<p align="center">
<img width="2294" height="400" alt="ex stats" src="https://github.com/user-attachments/assets/392f2668-6904-4a73-ac0d-f82e4a503f36" />
</p>

Par défaut, les graphes d'évolution des scores des 30 premiers joueurs sont générés, cliquer sur le bouton 'Générer plus de graphes' en génère 20 de plus à chaque fois.

Les checkbox sur la gauche permettent de filtrer les joueurs blessés ou qui ont déjà été pick dans les 30 derniers jours (cf. page Historique des picks).

Les indications sur la droite montrent les soirs avec moins de 3 matchs dans les 30 prochains jours pour pouvoir prévoir.

### 2. Historique des picks 
Gestion des picks : des rangées sont automatiquement ajoutées pour les soirs où des matchs ont eu lieu. Il suffit de rentrer le nom du joueur et de cliquer sur sauvegarder.

Les initiales des joueurs (SGA, KAT, ...), juste prénom/nom quand ils sont uniques (Jimmy, Chet, ...), et certains surnoms (Chef, Joker, Spida, ...) devraient aussi fonctionner. Pas besoin de capitaliser. Les fautes d'orthographe ou de frappe devraient aussi pouvoir être ignorées.

<img width="1364" height="739" alt="JDP" src="https://github.com/user-attachments/assets/ec3cc5f5-e094-4cf5-a469-26d0c58a5bbb" /><br><br>

## Installation

App développée avec python 3.13.3

### Clonage
```bash
git clone https://github.com/Ren3994/TTFL-Doctor.git
cd TTFL-Doctor
```

### Installation des librairies
```bash
pip install -r requirements.txt
```

## Utilisation

Lancer main.py. Le GUI se lancera et les données se mettront à jour. Selon la dernière fois où la base de donnée a été mise à jour, cela peut prendre quelques minutes. En règle générale, cela ne prend que quelques secondes.

Les données sont stockées dans des bases de données SQL pour que les calculs soient relativement rapides.

Vous pourrez modifier les picks dans la page Joueurs déjà pick et continuer à utiliser.

Note : Ce setup marche pour lancer à partir de VS Code

## Mentions légales

Ce projet est publié sous la Licence Publique Générale GNU Non-Commerciale (NC-GPL).

Vous êtes libre de consulter, utiliser, modifier et partager le code à des fins personnelles, éducatives ou non commerciales.

Toute utilisation commerciale nécessite une autorisation écrite explicite de l’auteur.

Ce projet utilise des api open-source, notamment :

- **nba_api** (Licence MIT)
  Copyright (c) 2018 Swar Patel

Plus d'informations : [nba_api](https://github.com/swar/nba_api).

## Auteur

Ce projet est développé et maintenu par Renaud Génin

© 2025 — Tous droits réservés le cas échéant.
