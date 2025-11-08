# 🏀 TTFL Doctor 

Application python pour aider à faire des choix sur la TrashTalk Fantasy League (TTFL) : https://fantasy.trashtalk.co

Disclaimer 1 : Ce projet est 100% personnel réalisé dans le but d'apprendre des techniques et n'est pas affilié à l'équipe de TrashTalk.

Disclaimer 2 : Je ne suis pas un bon programmeur.

## Pages disponibles : 

### 1. Classement TTFL du jour 
Donne le classement des joueurs TTFL jouant ce soir avec des informations sur les blessures et les stats TTFL.

<img width="1367" height="1003" alt="Classement" src="https://github.com/user-attachments/assets/b78e8c48-4ac5-4654-b594-eb8c98004469" /><br><br>

Cliquer sur les flèches à droite de la date, ou simplement rentrer une nouvelle date dans la case permet de naviguer entre les différentes journées de matchs.

Survoler certaines colonnes des joueurs fait apparaître des statistiques plus avancées (évolution des scores, stats par poste, maison/extérieur, influence des blessures des coéquipiers et des adversaires, ...)

Les checkbox sur la gauche permettent de filtrer les joueurs blessés ou qui ont déjà été pick dans les 30 derniers jours (cf. page Historique des picks).

Les indications sur la droite montrent les soirs avec moins de 5 matchs dans les 30 prochains jours pour pouvoir prévoir.

### 2. Historique des picks 
Gestion des picks : des rangées sont automatiquement ajoutées pour les soirs où des matchs ont eu lieu. Il suffit de rentrer le nom du joueur et de cliquer sur sauvegarder.

Les initiales des joueurs (SGA, KAT, ...), juste prénom/nom quand ils sont uniques (Jimmy, Chet, ...), et certains surnoms (Chef, Joker, Spida, ...) devraient aussi fonctionner. Pas besoin de capitaliser. Les fautes d'orthographe ou de frappe devraient aussi pouvoir être ignorées.

<img width="1364" height="739" alt="JDP" src="https://github.com/user-attachments/assets/ec3cc5f5-e094-4cf5-a469-26d0c58a5bbb" /><br><br>

## Utilisation

lancer main.py. La première fois, toutes les données seront téléchargées (peut prendre un peu de temps). Pour les fois d'après, ça ne devrait prendre que quelques secondes.

Les données sont stockées dans des bases de données SQL pour que les calculs soient relativement rapides.

Possibilité de précalculer les classements TTFL de plusieurs jours (car la génération des graphes peut prendre quelques secondes) en avance dans manager.py.

Une fois que les données sont mises à jour, un GUI Streamlit se lancera directement dans le navigateur. Le bandeau sur la gauche permet de naviguer entre les différentes pages.
