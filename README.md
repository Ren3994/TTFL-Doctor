# 🏀 TTFL Doctor 

Application python pour aider à faire des choix sur la TrashTalk Fantasy League (TTFL) : https://fantasy.trashtalk.co

Disclaimer : Ce projet est 100% personnel réalisé dans le but d'apprendre des techniques et de faire des best picks mais n'est pas affilié à l'équipe de TrashTalk.

Site hébergé sur streamlit community cloud : [TTFL Doctor](https://ttfl-doctor.streamlit.app)

## Pages disponibles : 

### 1. Classement TTFL du jour 
Donne le classement par moyenne TTFL décroissante de tous les joueurs jouant ce soir avec des informations sur les blessures et des stats TTFL.

<img width="1403" height="743" alt="Classement" src="https://github.com/user-attachments/assets/797309ac-f42e-43ca-9e38-f135eecc3b33" /><br><br>

Cliquer sur les flèches à droite et à gauche de la date, ou simplement rentrer une nouvelle date dans la case permet de naviguer entre les différentes journées de matchs.

Survoler certaines colonnes des joueurs fait apparaître des statistiques plus avancées (graphes des évolution des scores, stats par poste, maison/extérieur, influence des blessures des coéquipiers et des adversaires, ...). Par exemple :

<p align="center">
<img width="2294" height="400" alt="ex stats" src="https://github.com/user-attachments/assets/392f2668-6904-4a73-ac0d-f82e4a503f36" />
</p>

Par défaut, les graphes d'évolution des scores des 30 premiers joueurs sont générés, cliquer sur le bouton 'Générer plus de graphes' en génère 20 de plus à chaque fois.

Les checkbox sur la gauche permettent de filtrer les joueurs blessés ou qui ont déjà été pick dans les 30 derniers jours (cf. page Historique des picks).

Les indications sur la droite montrent les soirs avec moins de 2 matchs dans les 30 prochains jours pour pouvoir prévoir.

### 2. Historique des picks 
Gestion des picks : des rangées sont automatiquement ajoutées pour les soirs où des matchs ont eu lieu. Il suffit de rentrer le nom du joueur et de cliquer sur sauvegarder.

Les initiales des joueurs (SGA, KAT, ...), juste prénom/nom quand ils sont uniques (Jimmy, Chet, ...), et certains surnoms (Chef, Joker, Spida, ...) devraient aussi fonctionner. Pas besoin de capitaliser. Les fautes d'orthographe ou de frappe devraient aussi pouvoir être ignorées.

<img width="1356" height="671" alt="JDP" src="https://github.com/user-attachments/assets/9f03139f-d781-4dca-9474-fac363ecc864" /><br><br>

### 3. Top de la nuit

Donne les scores de tous les joueurs ayant joué lors de la nuit du jour renseigné dans la case. Si les picks sont renseignés dans la page Historique des picks, alors le pick sera surligné et la colonne 'Dispo' montre les joueurs qui auraient pu être pris à la place. Vous pouvez aussi voir les boxscores normaux par équipes en cliquant sur 'Boxscores par équipes'.

<br><img width="1343" height="767" alt="top nuit" src="https://github.com/user-attachments/assets/d4952412-5e7f-4de8-820e-d17f0c545529" />

### 4. Scores TTFL en direct

Montre les boxscores classiques en direct (mis à jour toutes les 15s) avec une colonne TTFL. Cliquez sur le bouton d'un match pour afficher le boxscore et recliquez pour le cacher. L'équipe et la rangée du pick est surlignée si le pick est renseigné.

<img width="1410" height="797" alt="live boxscores" src="https://github.com/user-attachments/assets/7f291fdc-258a-42dc-9149-e6c7d231006c" />

### 5. Stats par équipes (en construction)

Donne les stats par équipes (offensive rating, defensive rating, TS%, EFG%, pace, ...) plus différentes stats de TTFL d'équipe (quelles équipes fait les meilleurs scores, quelles équipes sont les meilleurs spots TTFL, ...). 

Cliquer sur les en-têtes des colonnes permet de classer le tableau par ordre croissant/décroissant par rapport à cette colonne.

<img width="1360" height="732" alt="team_stats" src="https://github.com/user-attachments/assets/0bbbc069-bb0b-47b1-83aa-451201368929" />

### 6. Stats par joueurs (en construction)

Donne les stats des joueurs. Classable par colonnes.

<img width="1364" height="757" alt="player_stats" src="https://github.com/user-attachments/assets/9230316f-d507-401a-b428-bfbcd07d6cda" />

## Installation

Vous pouvez juste utiliser l'appli hébergée sur streamlit : [TTFL Doctor](https://ttfl-doctor.streamlit.app)

Ou alors cloner le repo et travailler avec une version locale (app développée avec python 3.13.3).

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

### Version en ligne

Il suffit d'accéder au site. Pensez à renseigner vos picks dans la page 'Historique des picks' pour profiter de toutes les fonctionnalités.

### Version locale

Il faudra créer un fichier streamlit_interface/.streamlit/secrets.toml avec dedans :
```bash
environment = "local"
```

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
