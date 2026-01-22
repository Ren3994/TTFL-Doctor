import os

LEAGUE_ID = "00"
SEASON = "2025-26"
LAST_SEASON = "2024-25"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "..", "data", f"data_{SEASON}.db")
DB_PATH_LAST_SEASON = os.path.join(BASE_DIR, "..", "data", f"data_{LAST_SEASON}.db")
DB_PATH_HISTORICAL = os.path.join(BASE_DIR, "..", "data", f"historical_data.db")
DB_PATH_HISTORICAL_ZST = os.path.join(BASE_DIR, "..", "data", f"historical_data.db.zst")
CHECKSUM = '97cbf71cc22034d78a3fb964d70224155a2d6e8923a133cfb34e494cdbb7fa59'
HIST_DB_URL = 'https://github.com/Ren3994/TTFL-Doctor/releases/download/data_v1.1/historical_data.db.zst'

CACHE_DIR_PATH = os.path.join(BASE_DIR, "..", "data", "cache")
BACKUP_DIR_PATH = os.path.join(BASE_DIR, "..", "data", "backups")
PLOT_GEN_WORKER_PATH = os.path.join(BASE_DIR, "..", "streamlit_interface", "plotting_worker.py")

FAILED_LOG_PATH = os.path.join(BASE_DIR, "..", "data", "failed_games.log")
OG_TEAM_LOGOS_PATH = os.path.join(BASE_DIR, "..", "data", "team_logos")
RESIZED_LOGOS_PATH = os.path.join(BASE_DIR, "..", "data", "team_logos_150")
TBD_LOGO_PATH = os.path.join(BASE_DIR, "..", "data", "team_logos_150", 'TBD.png')

STREAMLIT_MAIN_PY_PATH = os.path.join(BASE_DIR, "..", "streamlit_interface", "streamlit_main.py")
STREAMLIT_PAGES_PATH = os.path.join(BASE_DIR, "..", "streamlit_interface", "streamlit_pages")

MAX_WORKERS = max(1, os.cpu_count() // 2)
MAX_BKG_WORKERS = max(1, os.cpu_count() // 3)

TRICODE2NAME = {'ATL': 'Hawks', 'BOS': 'Celtics', 'BKN': 'Nets', 'CHA': 'Hornets', 'CHI': 'Bulls', 'CLE': 'Cavaliers', 'DAL': 'Mavericks', 'DEN': 'Nuggets', 'DET': 'Pistons', 'GSW': 'Warriors', 'HOU': 'Rockets', 'IND': 'Pacers', 'LAC': 'Clippers', 'LAL': 'Lakers', 'MEM': 'Grizzlies', 'MIA': 'Heat', 'MIL': 'Bucks', 'MIN': 'Timberwolves', 'NOP': 'Pelicans', 'NYK': 'Knicks', 'OKC': 'Thunder', 'ORL': 'Magic', 'PHI': '76ers', 'PHX': 'Suns', 'POR': 'Trail Blazers', 'SAC': 'Kings', 'SAS': 'Spurs', 'TOR': 'Raptors', 'UTA': 'Jazz', 'WAS': 'Wizards'}
NAME2TRICODE = {v: k for k, v in TRICODE2NAME.items()}
FULLNAME2TRICODE = {'Atlanta Hawks': 'ATL', 'Boston Celtics': 'BOS', 'Brooklyn Nets': 'BKN', 'Charlotte Hornets': 'CHA', 'Chicago Bulls': 'CHI', 'Cleveland Cavaliers': 'CLE', 'Dallas Mavericks': 'DAL', 'Denver Nuggets': 'DEN', 'Detroit Pistons': 'DET', 'Golden State Warriors': 'GSW', 'Houston Rockets': 'HOU', 'Indiana Pacers': 'IND', 'LA Clippers': 'LAC', 'Los Angeles Lakers': 'LAL', 'Memphis Grizzlies': 'MEM', 'Miami Heat': 'MIA', 'Milwaukee Bucks': 'MIL', 'Minnesota Timberwolves': 'MIN', 'New Orleans Pelicans': 'NOP', 'New York Knicks': 'NYK', 'Oklahoma City Thunder': 'OKC', 'Orlando Magic': 'ORL', 'Philadelphia 76ers': 'PHI', 'Phoenix Suns': 'PHX', 'Portland Trail Blazers': 'POR', 'Sacramento Kings': 'SAC', 'San Antonio Spurs': 'SAS', 'Toronto Raptors': 'TOR', 'Utah Jazz': 'UTA', 'Washington Wizards': 'WAS'}

IMG_CHARGEMENT = 'data:image/png;base64,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'
IMG_PLUS_DE_GRAPHES = 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAABG4AAACRCAYAAACSRv61AAAAOnRFWHRTb2Z0d2FyZQBNYXRwbG90bGliIHZlcnNpb24zLjEwLjcsIGh0dHBzOi8vbWF0cGxvdGxpYi5vcmcvTLEjVAAAAAlwSFlzAAAXEgAAFxIBZ5/SUgAANfpJREFUeJzt3QfYHFW9+PGhhC69CkgvIlzAIFJCz1VEiAQUgQABRJSiEqpcCFWEEIHgJQKJVBVCroQWREpowkXRgChw6cUgHQRCb/N/vvN/Zp+zmy2zu7O7s6/fz/OsJmHf3Xln5pQ55/c7Z7Y4juNIkiRJkiRJhTN7rw9AkiRJkiRJ1TlwI0mSJEmSVFAO3EiSJEmSJBWUAzeSJEmSJEkF5cCNJEmSJElSQTlwI0mSJEmSVFAO3EiSJEmSJBWUAzeSJEmSJEkF5cCNJEmSJElSQTlwI0mSJEmSVFAO3EiSJEmSJBWUAzeSJEmSJEkF5cCNJEmSJElSQTlwI0mSJEmSVFAO3EiSJEmSJBWUAzeSJEmSJEkF5cCNJEmSJElSQTlwI0mSJEmSVFAO3EiSJEmSJBWUAzeSJEmSJEkF5cCNJEmSJElSQTlwI0mSJEmSVFAO3EiSJEmSJBWUAzeSJEmSJEkF5cCNJEmSJElSQTlwI0mSJEmSVFAO3EiSJEmSJBWUAzeSJEmSJEkF5cCNJEmSJElSQTlwI0mSJEmSVFAO3EiSJEmSJBWUAzeSJEmSJEkF5cCNJEmSJElSQTlwI0mSJEmSVFAO3EiSJEmSJBWUAzeSJEmSJEkF5cCNJEmSJElSQTlwI0mSJEmSVFAO3EiSJEmSJBWUAzeSJEmSJEkF5cCNJEmSJElSQTlwI0mSJEmSVFAO3EiSJEmSJBWUAzeSJEmSJEkF5cCNJEmSJElSQTlwI0mSJEmSVFAO3EiSJEmSJBWUAzeSJEmSJEkF5cCNJEmSJElSQTlwI0mSJEmSVFAO3EiSJEmSJBWUAzeSJEmSJEkF5cCNJEmSJElSQTlwI6lwPv3002jo0KHRbLPNlrzWXXfdaObMmVE/ePnll6NlllmmdOzf+c53en1IkiRJkvqYAzeSCufUU0+Npk2blvz5s5/9bHT99ddHn/nMZ6Kii+M42nPPPaMXX3wx+fvWW28dnXfeeb0+LEmSJEl9rGsDNx9++GF09913R1dccUU0fvz46JRTTonOPvvs6NJLL43+9Kc/Re+//36mz7n99ttLM9m8nnnmmZrvXXHFFUvvO+GEE3L8baR/j6iX++67L7ryyiujCRMmJIMpP/vZz6KJEydG11xzTd2y1w7qieOPPz758/zzzx9dd9110XLLLRf1gzFjxkQ33XRT8ufPf/7zybkbNGhQrw9LURTtvffepfZgyy237PXh9BXPnVIXX3xxWR9MUn8o4jMR/ciwPuEZT1Jtc0Ydnn2ePHly0tDfeeed0bvvvlv7QOacMxoyZEgyW73LLrtECyywQCcPTer7B6lLLrkk+TODHGEjzIPVHXfckfz5oosuSt7bjKlTp0a//OUvk89444036r534YUXjr761a9G3/zmN6Ovf/3r0bzzzhu14/XXX49222236JNPPolmn3326LLLLou++MUvRv3gnnvuiUaPHp38eYkllkiihDg/kqSB+SD87LPPJn++7bbbygY1w0Gtp59+OnmvJHUaz9zpxOp6660X7bjjjr0+pORZYty4caW/81xinViwgRvSHEaNGhX9/e9/z/T+jz/+OBlp5XX00UdHxx13XPS9730vGdCR1Hl/+MMfkjI7ffr0pipjouh4LbXUUtGRRx4ZHXDAAS0P4Oy7777RjBkzkj+fccYZ0bBhw6J+wHlgwIl6bJ555omuvfbaaKWVVur1YUmSJOnfaOAmnbwdOXJkYQZuTjzxxNLfGeR24KY1HRkV+fnPfx4deuihyax5OPvwH//xH9FWW22VrFmx2GKLRW+99Vb00ksvRffff38yYPPBBx+UFvc8+OCDo0033TQZLZTUWeecc04yaMPAQ2j11VdPyuznPve5pMxSjlm/5Z///Gd06623Rk888UTpvZTlww47LPmZ7bffvulj+O///u8kBQsHHXRQdMghh0T9ggWImXnl/BAJtdFGG/X6kCRJkiQNELkP3Jx88slJtEyKBxlmovn3lVdeuebPvfPOO8msPSNy//jHP3I5lk6twSENJNXKLOmKpGCxTks9jz/+eLL4Lq96qZCNMHh7xBFHJH/+2te+lqx/1S9+8YtfRFOmTEn+zNpdnDtJkqSi8JlI6n+5Lk7MopzhWhtzzTVXMhjzm9/8pu6gTboIKWkSPAjywMj6FpI664Ybbigrs6Q4/fa3v40mTZrUcNAGq622WpLSRIegnW2v119//WSBctbF+t3vfhfNMcccUb848MADk+PmRZqnJEmSJBUy4obZdhYWZieaFAM2LFraDAZ7eJAk1aCX2//++c9/jv72t79Fr7zySpIiQi7eFltskRxfP3j77beTNUuee+656NVXX03O5bLLLpvkFS6yyCJRv2FXsr/+9a/Rgw8+mCxgy0M+gwyLL754spYIKXULLrhgVFQPPfRQst7TCy+8kKQEsuDuV77ylZ7fI3vttVdZmf2f//mfZJHhZrEYLwsas1BxKwvysngjZY50K6Lv+Lw11lgj2njjjXMbxLn33nuj//u//0uuAYufr7rqqkl5YE2aVjFYw85bDz/8cJLiyd9Z62fw4MHRWmutldu9T1kmFYvzM99880Xf+MY36uYHc4+xOxcDahwXZWWZZZaJNt9882jppZfO5bj+9a9/Jcf1/PPPJ2WSepI2gOPLG+eAnG1+n9deey1acsklk9TbDTbYIOpn1M1/+ctfoieffDJ68803k2g3JjGoqxkU/cIXvtDxQUzKHvcK15Frxw5u3CeLLrport/R6fKdBW0IL9I9qadIAaUOyPuebbbMkv9Pf4OJK8rSRx99lLTTXAtSxvO8FrRDfBfprtQLtJ9bb711buegX+pZyhvruT366KPJn2kHOQfUkxzzOuus0zf9vRSpy/xO9PsoV9zfXNt2FsnnvFB2uaace9ad5NzTh8kyuVMErbShRUK9wDXg/NO20/5Rf375y1/u+iRX0c4l6f3sTMy9z/Fwf9LHoW1pdZ3BXrbLRXrW4fmXtoLzQH+Pepe2iGvN+e3FM/qbA7Deblqck3HjxsV8XPrac88940647bbbyr7n6aefrvneFVZYofS+448/PtPnX3PNNfGqq65a9h3pa7HFFouPO+64+KOPPmrq88PPuOiii3L/PUN//etf4x122CGea665qv4Oc845Zzxs2LD40Ucfber7m31tscUWcR7eeuut+Mgjj0zOfb3vm3322eMvfvGL8YQJE6p+DucvfD+/XxZcr/Dnmr1ev/3tb+N11lkn9/MzcuTImvcen53lfjvjjDPKjun73/9+3E2ffPJJfOGFF8ZrrrlmzevKdT/xxBPj9957r+Vrdfnll8err7561c9fYIEF4lNOOSX++OOPm74vjznmmHippZaqeeyrrbZafNlllzV9PdN745133okPPfTQeJFFFpnls2td16eeeioeMWJEPN9881U9ptlmmy35/HvvvTfTcVWr45555pl4p512qlrHZK2nquHz08/he0FdS51bq/xzjq+99tqWz3E772unvbn//vvj7bbbLp5jjjnq1mvzzz9/vOOOO8Z/+9vf4rw9+OCD8ZZbbln1e+eee+549913j1955ZWWz0ne5bsdN9xwQ83jWHDBBeMf/ehH8bvvvjtL/cnv3aky+8gjj8QnnHBCPHjw4KT9qnWOKLPbbLNNfMcdd2T6XWu1dTfffHO8/vrr16wHDz/88NI5GKj1LJ588sl41113Te7xemWP//6Vr3yl7nkPy3xlnyKverFStXvqvvvuizfbbLOav8e+++4bv/766019D/cy9+cSSyxR8xytssoq8QUXXJCU9Vbq9yy6VR6zmDJlStlnZC2Tqauvvrrs52+66aaa7/3000/jX//61/Eaa6xR8/wvuuii8dFHHx3PnDkz1zaqG+ey3b75Sy+9FB944IHxwgsvXPP8UN/deOONmY+ll+1yu886rTyzVbsHpk+fHh9xxBHxWmutVfdnOUfDhw9PnjnrCe+lrK9q9WWe9Xa/y2Xghkr7c5/7XFlHg5PcbwM33KxZbqrNN988fvvttws3cDN69Oi6HcDwxUPXFVdckfn7ezFwM2PGjJqDaLVem266aWEGbg4++OCOnZ92B24os8suu2xZJfyPf/wj7pYXX3wx3nDDDTNfVxqRf/7zn01fq3rXIHztsssuSUcpi3vuuafug0Tl61vf+lb84Ycf1v3Myo4S16LeA2+163reeefVHLCtfFFHn3nmmQ1/18o6joe/hRZaqObn5jlwQx1LXZvl96HD0y8DN3TGG3UMK18TJ06M88QDSJZ7Zfnll48ffvjhps9JJ8p3q2gXsxwDA+wvvPBCyw+KzZbZ8HuyltmTTz654e9bra1jYi1L32DttdeOX3755QFbz06bNq3moHatFwNHRR64mTx5cjzPPPM0/D1o7x9//PFM38H7Vl555cznaKuttorffPPNQg3ctNKGNvLBBx8kgyXpZ+y3335N/fzOO+9cdj1qDXgxSPK1r30t8/lP6+lODdx04ly20zdnsuYzn/lM5vMzatSohp/Zy3Y5j2edvAZuwnsky4t+BBM0nRy4ybve7ndz5hV6Gy4o/J//+Z8N17QpmjFjxkRjx44t/Z3QOH6PoUOHJqFhhBVfddVVSQjb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Zptttsy/58UXX1z23k033TR+8MEH43o+/fTT+J577okPOOCAePDgwbP899GjR5d95t577x1305Zbbhlvvvnm8aRJk+J33nmn5vs++uij+NBDDy071vPPP7/qe6+77rqy933961+P33333Vne9+abb8YjRoyoeh1qaea+LBru3fDY+Z133XXXpFw08uGHHybXKCxr9c7Txx9/HA8dOrSsfjjmmGOSc17PW2+9lXzPFltsEZ922mlV33PRRRdlOoZKI0eOLP0Mn1/LCy+8EC+zzDKl9y688MLxpZdemvxO9Tz33HPxuHHj4tVWWy0pc+0cQzXTpk2L55hjjtLPr7XWWvHdd9/d8OceeOCB+Kijjoo/+9nPtl2H5n0fhnXseeedV/X9t9xyS3IN0p+Za6654ocffrjm5zdzjqkT0/fOM8888U033VT1ffz7IossMktdUe1cUSfMO++8SZ37pz/9qe73P/vss/Haa69d+jx+7o033ojb9d5778WrrrpqWVk/++yzq773D3/4Q7zEEkvM0tbVO3edLN/N+uSTT+INN9xwlrbxzjvvTNo/8P+Ula222ir57/PNN1+84oorlt7PPVNLO2V23XXXLbu2te4v7gM+u/Ia1Gtj+PfKPhj/v/3228evv/76LO9/+eWX42222absZ4499tiax96v9eycc86ZtOu33nprcm/UQt+M/kdYRh555JG4KKpd2y9/+cvxjBkzZnnvzJkz4912263sZ/bYY4+an015CMsvr/33379qP+n555+PN9tss7L3/vjHP6577DvvvHPZeaXvWs306dNLbU9Yr3aqPLaLey8sn2EdS7tUrb9fy8knn1x2TjfeeOOq15bnhQMPPHCW+q3evZ21Pe/muaysr2o9e4HnmgUWWKD03mWXXTaeOnVqw+94/PHH45/85CfJ+6lfitQud+JZh88K33fmmWcmP18P/32xxRYr/Qxtf7Vn8PQ6pOehsl2qZ9ttty29j35nrc8fiPV2nnLZVSrEIkFEgDBSzMgms0RE4rCIEuHLbCvGopqkaDBaz0wYufDk6tabEeokQqpPPvnk0mwhsxesqM2K8dtss0206KKLJiN5pH6lefsjR45MjvnZZ59t+Plrr712EgKcRjIwGk/YKBEtn//855MIGSJ4+O/M+DFrwSzKSSedlOn4ORZCB8eOHZv8nZBYvnOTTTZJFtIin5mFBhmV53wzYstMarroW7XFPCujjsgpXXXVVaNmZq3DLeKbRf+EY+DFsbNmAfm/6YKszBAyI896O+E1IC+TWYtqSKEgzYutr0FaENdhxIgR0SqrrJLM9LLIG9fhtddeSxZfZkQ5Pa8DFRFujIQz40qZ5dxPmjQpebHIHbnFjMZTZpkx49yTQsJMKPdF5YwQ57JeHjefy8wJIZbUD0Ry/fznP0/K2+DBg5OdRYgC4nMJwWaGg3U20lnUbbfdNuoFIjm4N/h+6i7C1JlJY+cBtoQkXJpQzXShWu7P+++/P7mn6s1atou6ihSPdHaU67Lpppsm9S3XjhQZ7mWuG7MRzHRwPtO0iDx3RMgLdRY7n5GaSRkkXWfHHXdMFkulfmYBfF7heaW+pD7Nq0ykYevUC9ybfD/tF5Fq3P+ECadrorG7BKHbjdoDZrHJw+ZF5AV1NIv7c89Ttpj5I8qREPkw8oTjaXX70xCzuRdccEGSEsF9yvkjGoMdGYYPH54skMl9TSQTqTOUT9pH7u0sKRlFKt9EALHzIW1gmu5G28jfWYOD46CeDxdKJaWKCKN0lq9Ta7zQvqcLKXJPcG5I26YsU89Sf7AYZXof0Cegb3X88ce39F0//elPkxlU6nO+l/4B155zzzkK1zAiMoI6rVc6Vc/Sz6JPwov1XSh71JGk+HM/UK+wzS/9vHDHUOqfdhc87xTWlvzFL36RlB/KKRGzpCyyngTlj2sbRiVQ54Q7mlWiXFIX0E9ifUNQ99JX4r7hPBC1QD+YrYvD88TPNFrb8thjj01SsLgWXCsiyXg24N7nmlL/0a8mLZC6g+tN+QyjV4qIdomym6bvsNNQiuwBniGyOvroo5O2Le2DUw/QrhHtzrWlvSZqf/LkyWWpjdQbpBZm3T2vH1H2eZ7kXqT881xGxgT12tChQ5P7k+cD6kzqdsoAz1uNMiR62S534lmHJS449jT6hHqCskc/Pox6o25Lo2ZoY9hmPN2ti9+ZMk2/h2gn+pD8G8dJ34BnBY7vgAMOiMaMGZPpd2WnrHStLfpQtDXU96Q3hfctu1nx+w/UerttcYfcfPPNZSOTzbyYbZkwYULVGZZORNyk0miXRi9GR4kQaubzX3zxxXjNNdds+NmMzl9yySUtRXCMHz8++flmzzcz9JXSWb5WX+2O0rfy/cxiMgtUDyOwSy+9dMPPWnDBBeMbb7wx8+xiP0fchL/Deuut1/I1X3zxxeMzzjgj/uCDDxp+F7MUzAC38j2nn356T2aCU0R1rL766i0d+7333pvLMVQzZcqU5L5t9piIMihaxA3fSx1LXZvldzjiiCMafn6z53jUqFGZvnvYsGHJPd/oXFXOLGZ9HXnkkXHerrzyykxtxfLLL5/c782eu06U71Y98cQTSURCve9k5pR2FxtttFHp3w855JCan9tumf3BD36Q6XzMPffcSWRC1jam2gz2WWedNcvMaLXXF77whSQCp55+rWdb+RxmeokqLZLw+LgWkydPTqICG/0uRBs89thjmb6DCIWVVlop83liprtRVF2KqKgsn0k5/Ne//lXWFyxqxA2ICqv2e1x11VVNfxaRF2F0QqPXcsstlylCut8jblJ33XVXpn58tddLL71U9/u73S536lnnhhtuKItOqvaqvAd45v7GN76R6RgWWmih+Pe//33T7cF+++3X8LPDtm2g1Nt56tjATRp2efnll8df/epXk4eDeieaVCXCdek8VQvL7MbADa6++uqyMMfwRRgZKURpyFmzn//KK68kFWKtDtSQIUOSENFmf88QIZWET6bh+/U6qoTEMthTLYyz1wM3hOkfdNBBmTpuK6+8cjx27NjMBZVzycNWtc/i2my33Xbxk08+mbz332ngJiwDnB8q5kbnnjIxfPjw5EEwy4BNJQbHSFMgHLLe9xBWSdmhoagVMt+tBwpwrxGmyoNOloHRww47rG5YaF4dpVdffTU++uijG3ZqqG8Jqx4zZkwS5l3EgRtQ11LnhiG84Yu6+pprrsn0+a2cY9K0llxyyZr3JA8hadpNo3NFaPvEiROTjlGj+pl6iPr5jjvuiDuFcOda9TyDBbvvvnvSZrVzf+ZZvttBiDV9Eeo1BqP4/biupMSdcMIJSQh8Kmxz+G+dLLPcDzxQVzsnpD9yD5DSiHYGbtLJtFoD8/PPP38ycVWv79Xv9exvfvObJG1oqaWWyjRowEB4EYXHybXAfffdN0vaUvpigHafffZpKl0nHTygHkvTJau9VllllfiXv/xl3RSGaugvhCmJ4YulCsJ+dr8M3DDRUPmgTLvV6gMk7cqvfvWreI011qh5/jlXpKeRaprFQBm4Sc83/ZdGA4y0pdTzxx13XDIgWbR2uZPPOrRrpL3S16McV07WVLsHKMunnnpqcm/Vqk922mmn+Jlnnmm5PSA1eK+99krqbCYb66UBD5R6O0+z8T9RFxDWRooKqUCEbxEmTcg54ZGEMxH6VKSQfUJPSSkiNIwQRBbNI3Q/DDNj4aM0dI0QZsLmsuD3J8WE8G3CwAhPZwvbLKvOZ0WYKeGshAryfYTbcb4JNeN8E3JYpPNdD8fPtWCxOsLiSKkjpJAQO0Ltwt0KmkGYJWG5hOwRpsd1IMWE/9f/X9SQEHTSBrgGnHvuf9KqCMNk20/ScPJAiCNpDNQPhLiCMExCOwkBD3cEKxruozT1kNB9zhH1GiljpCSEq9x3EylRpA9Qh5EmSZnhuhFWzHHx9yKh/kxD7bnu4aJ0tB+UVf6N+4NzSqhwu1t/Z0Edzb1JOippG3w3aaOk3LSaSkOz+9hjjyUh3IS7c/+TpsA9z31DqDTXqhuoV/n9qAfZZIA0NX63ZsL7B0r5Ji2D0Pd0gX/SOEil7SRST+hvUFapP6hf2TSBkPBWFtqmjITnk74GKX4p2lJSpLjepM7RjyHNgGtfZHnWs6To0Tei/0ZflP4SqQDcj2maQlGFmwmwKDrpRilSdEgN4VzRp6Esk+7PeWoV54a+O+eLHYxIqaAfSdpOuHNbK59L+glpDvQtuO+5b0nv7Ze+abfQTnBdufdpC7nX6ceTVtOpdM5+wn0/ffr0pK9DeaZeo/3imYq6IVwUt8jtcqeedVpB+hhtNuWe88BzMPUifYOs5zNv/Vxv56lrAzcDUasDN5Kk7AM3UjeQJ89aPyk6id3sLOeh0cCN+lu9gRtJ0sA2cFexkiRJyhhhGC6yyODHgF3cUJIk9R0HbiRJ0oBDagHh1Y0Qcs3uWqTipL773e+WRTdIkiT1kgM3kiRpwGHQJt0Ce8qUKckaHSFy96+66qpkbbPx48eX/p31DH74wx/24IglSZKqm7PGv0uSJPU1FhqePHly8gILK7IAMQv2swAk0TYhFnKdNGlS4RbvliRJ/94cuJEkSQPOoEGDZvk3dgbjVQ27tFx44YV9tyCxJEka+By4kSRJA87gwYOTrVWnTp1a2tqULclnzpyZ/He2jGUL0c022ywaNmxYsnWyJElSEbkduCRJkiRJUkG5OLEkSZIkSVJBOXAjSZIkSZJUUA7cSJIkSZIkFZQDN5IkSZIkSQXlwI0kSZIkSVJBOXAjSZIkSZJUUA7cSJIkSZIkFZQDN5IkSZIkSQXlwI0kSZIkSVJBOXAjSZIkSZJUUA7cSJIkSZIkFZQDN5IkSZIkSQXlwI0kSZIkSVJBOXAjSZIkSZJUUA7cSJIkSZIkFZQDN5IkSZIkSQXlwI0kSZIkSVJBOXAjSZIkSZJUUA7cSJIkSZIkFZQDN5IkSZIkSQXlwI0kSZIkSVJBOXAjSZIkSZJUUA7cSJIkSZIkFZQDN5IkSZIkSQXlwI0kSZIkSVJBOXAjSZIkSZJUUA7cSJIkSZIkFZQDN5IkSZIkSQXlwI0kSZIkSVJBOXAjSZIkSZJUUA7cSJIkSZIkFZQDN5IkSZIkSQXlwI0kSZIkSVJBOXAjSZIkSZJUUA7cSJIkSZIkFZQDN5IkSZIkSQXlwI0kSZIkSVJBOXAjSZIkSZJUUA7cSJIkSZIkFZQDN5IkSZIkSQXlwI0kSZIkSVJBOXAjSZIkSZJUUA7cSJIkSZIkFZQDN5IkSZIkSQXlwI0kSZIkSVJBOXAjSZIkSZJUUA7cSJIkSZIkFZQDN5IkSZIkSQXlwI0kSZIkSVJBOXAjSZIkSZJUUA7cSJIkSZIkFZQDN5IkSZIkSVEx/T9wrC484yPqIQAAAABJRU5ErkJggg=='

FRENCHIES = set(['Nicolas Batum', 
                 'Joakim Noah',
                 'Evan Fournier', 
                 'Rudy Gobert', 
                 'Timothe Luwawu-Cabarrot', 
                 'Ian Mahinmi', 
                 'Frank Ntilikina', 
                 'Elie Okobo', 
                 'Tony Parker', 
                 'Guerschon Yabusele', 
                 'Tariq Abdul-Wahad', 
                 'Jerome Moiso', 
                 'Antoine Rigaudeau', 
                 'Boris Diaw', 
                 'Mickael Pietrus', 
                 'Johan Petro', 
                 'Ronny Turiaf', 
                 'Mickael Gelabale', 
                 'Alexis Ajinca', 
                 'Rodrigue Beaubois', 
                 'Kevin Seraphin', 
                 'Pape Sy', 
                 'Nando De Colo', 
                 'Damien Inglis', 
                 'Joffrey Lauvergne', 
                 'Axel Toupane', 
                 'Sekou Doumbouya', 
                 'Jaylen Hoard', 
                 'William Howard', 
                 'Adam Mokoka', 
                 'Vincent Poirier', 
                 'Killian Tillie', 
                 'Killian Hayes', 
                 'Theo Maledon', 
                 'Petr Cornelie', 
                 'Joel Ayayi', 
                 'Yves Pons', 
                 'Olivier Sarr', 
                 'Ousmane Dieng', 
                 'Moussa Diabate',
                 'Malcolm Cazalon', 
                 'Sidy Cissoko', 
                 'Victor Wembanyama', 
                 'Rayan Rupert', 
                 'Bilal Coulibaly', 
                 'Pacome Dadiet', 
                 'Zaccharie Risacher', 
                 'Tidjane Salaun', 
                 'Alex Sarr', 
                 'Melvin Ajinca', 
                 'Armel Traore', 
                 'Joan Beringer', 
                 'Noa Essengue', 
                 'Nolan Traore', 
                 'Noah Penda', 
                 'Maxime Raynaud', 
                 'Mohamed Diawara', 
                 'Daniel Batcho', 
                 'Adama Bal'])

TEAM_TRICODE2IDS = {
    'ATL': 1610612737,
    'BOS': 1610612738,
    'BKN': 1610612751,
    'CHA': 1610612766,
    'CHI': 1610612741,
    'CLE': 1610612739,
    'DAL': 1610612742,
    'DEN': 1610612743,
    'DET': 1610612765,
    'GSW': 1610612744,
    'HOU': 1610612745,
    'IND': 1610612754,
    'LAC': 1610612746,
    'LAL': 1610612747,
    'MEM': 1610612763,
    'MIA': 1610612748,
    'MIL': 1610612749,
    'MIN': 1610612750,
    'NOP': 1610612740,
    'NYK': 1610612752,
    'OKC': 1610612760,
    'ORL': 1610612753,
    'PHI': 1610612755,
    'PHX': 1610612756,
    'POR': 1610612757,
    'SAC': 1610612758,
    'SAS': 1610612759,
    'TOR': 1610612761,
    'UTA': 1610612762,
    'WAS': 1610612764
}

TEAM_IDS2TRICODE = {v: k for k, v in TEAM_TRICODE2IDS.items()}

CHAR_MAP = {
    "ć": "c",
    "č": "c",
    "Č": "C",
    "é": "e",
    "í": "i",
    "Š": "S",
    "ö": "o",
    "ū": "u",
    "ņ": "n",
    "ģ": "g",
    "ô": "o",
    "ü": "u",
    "Đ": "D"
}

NICKNAMES = {'KD' : 'Kevin Durant',
             'KING' : 'LeBron James',
             'LBJ' : 'LeBron James',
             'BEARD' : 'James Harden',
             'BRODIE' : 'Russell Westbrook',
             'RUSS' : 'Russell Westbrook',
             'CHEF' : 'Stephen Curry',
             'STEPH' : 'Stephen Curry',
             'CP3' : 'Chris Paul',
             'AD' : 'Anthony Davis',
             'DAME' : 'Damian Lillard',
             'JOKER' : 'Nikola Jokic',
             'PROCESS' : 'Joel Embiid',
             'BOOK' : 'Devin Booker',
             'SPIDA' : 'Donovan Mitchell',
             'ANTMAN' : 'Anthony Edwards',
             'ANT' : 'Anthony Edwards',
             'WEMBY' : 'Victor Wembanyama',
             'ALIEN' : 'Victor Wembanyama',
             'HALI' : 'Tyrese Haliburton',
             'AR15' : 'Austin Reaves',
             'AR-15' : 'Austin Reaves',
             'FVV' : 'Fred VanVleet',
             'ZU' : 'Ivica Zubac',
             'VUC' : 'Nikola Vucevic'
             }

TEAM_STATS_COLUMN_DEF = {
    
    # Regular stats
    'teamTricode' : {'col' : 'text', 'display' : 'Équipe', 'format' : None, 'width' : None, 'help' : None},
    'GP' : {'col' : 'num', 'display' : 'GP', 'format' : None, 'width' : 30, 'help' : 'Nombre de matchs joués'},
    'W' : {'col' : 'num', 'display' : 'W', 'format' : None, 'width' : 30, 'help' : 'Nombre de matchs gagnés'},
    'L' : {'col' : 'num', 'display' : 'L', 'format' : None, 'width' : 30, 'help' : 'Nombre de matchs perdus'},
    'W_PCT' : {'col' : 'num', 'display' : 'W%', 'format' : "%.0f%%", 'width' : 50, 'help' : 'Pourcentage de matchs gagnés'},
    'PTS' : {'col' : 'num', 'display' : 'Pts', 'format' : '%.1f', 'width' : 50, 'help' : 'Moyenne de points marqués'},
    'AST' : {'col' : 'num', 'display' : 'Ast', 'format' : '%.1f', 'width' : 50, 'help' : 'Moyenne de passes décisives'},
    'REB' : {'col' : 'num', 'display' : 'Reb', 'format' : '%.1f', 'width' : 50, 'help' : 'Moyenne de rebonds'},
    'OREB' : {'col' : 'num', 'display' : 'Oreb', 'format' : '%.1f', 'width' : 50, 'help' : 'Moyenne de rebonds offensifs'},
    'DREB' : {'col' : 'num', 'display' : 'Dreb', 'format' : '%.1f', 'width' : 50, 'help' : 'Moyenne de rebonds défensifs'},
    'STL' : {'col' : 'num', 'display' : 'Stl', 'format' : '%.1f', 'width' : 50, 'help' : 'Moyenne d\'interceptions'},
    'BLK' : {'col' : 'num', 'display' : 'Blk', 'format' : '%.1f', 'width' : 50, 'help' : 'Moyenne de tirs contrés'},
    'TOV' : {'col' : 'num', 'display' : 'Tov', 'format' : '%.1f', 'width' : 50, 'help' : 'Moyenne de balles perdues'},
    
    # Advanced stats
    'AST_TO' : {'col' : 'num', 'display' : 'Ast/tov', 'format' : '%.1f', 'width' : None, 'help' : 'Moyenne de passes décisives divisée par la moyenne de balles perdues'},
    'AST_PCT' : {'col' : 'num', 'display' : 'Ast%', 'format' : "%.1f%%", 'width' : 60, 'help' : 'Pourcentage de tirs marqués après une passe décisive'},
    'REB_PCT' : {'col' : 'num', 'display' : 'Reb%', 'format' : "%.1f%%", 'width' : 60, 'help' : 'Pourcentage de rebonds captés'},
    'OREB_PCT' : {'col' : 'num', 'display' : 'Oreb%', 'format' : "%.1f%%", 'width' : 60, 'help' : 'Pourcentage de rebonds offensifs captés'},
    'DREB_PCT' : {'col' : 'num', 'display' : 'Dreb%', 'format' : "%.1f%%", 'width' : 60, 'help' : 'Pourcentage de rebonds défensifs captés'},
    'Pace' : {'col' : 'num', 'display' : 'Pace', 'format' : '%.1f', 'width' : None, 'help' : 'Nombre de possessions par match'},
    'ORtg' : {'col' : 'num', 'display' : 'ORtg', 'format' : '%.1f', 'width' : None, 'help' : 'Moyenne de points pour 100 possessions'},
    'DRtg' : {'col' : 'num', 'display' : 'DRtg', 'format' : '%.1f', 'width' : None, 'help' : 'Moyenne de points marqués par les adversaires pour 100 possessions'},
    'NRtg' : {'col' : 'num', 'display' : 'NRtg', 'format' : '%+.1f', 'width' : None, 'help' : 'Différence entre Ortg et Drtg'},
    'TM_TOV_PCT' : {'col' : 'num', 'display' : 'Tov%', 'format' : "%.1f%%", 'width' : 60, 'help' : 'Pourcentage de possessions qui finissent en balle perdue'},
    'BLKA' : {'col' : 'num', 'display' : 'BlkA', 'format' : '%.1f', 'width' : None, 'help' : 'Moyenne de tirs tentés qui se sont fait bloquer'},
    'PFD' : {'col' : 'num', 'display' : 'Fau. prov.', 'format' : '%.1f', 'width' : None, 'help' : 'Moyenne de fautes provoquées'},
    'AST_RATIO' : {'col' : 'num', 'display' : 'Ast ratio', 'format' : '%.1f', 'width' : 60, 'help' : 'Moyenne de passes décisives pour 100 possessions'},
    'FG3_ratio' : {'col' : 'num', 'display' : 'Ratio 3pts', 'format' : "%.1f%%", 'width' : None, 'help' : 'Pourcentage de tirs tentés qui sont des 3 pts'},

    # Shooting stats
    'FGM' : {'col' : 'num', 'display' : 'FG', 'format' : '%.1f', 'width' : 50, 'help' : 'Moyenne de tirs marqués'},
    'FGA' : {'col' : 'num', 'display' : 'FGA', 'format' : '%.1f', 'width' : 50, 'help' : 'Moyenne de tirs tentés'},
    'FG_PCT' : {'col' : 'num', 'display' : 'FG%', 'format' : "%.1f%%", 'width' : 60, 'help' : 'Pourcentage de tirs réussis'},
    'FG3M' : {'col' : 'num', 'display' : 'FG3', 'format' : '%.1f', 'width' : 50, 'help' : 'Moyenne de tirs à 3 points marqués'},
    'FG3A' : {'col' : 'num', 'display' : 'FG3A', 'format' : '%.1f', 'width' : 50, 'help' : 'Moyenne de tirs à 3 points tentés'},
    'FG3_PCT' : {'col' : 'num', 'display' : 'FG3%', 'format' : "%.1f%%", 'width' : 60, 'help' : 'Pourcentage de tirs à 3 pts réussis'},
    'FTM' : {'col' : 'num', 'display' : 'FT', 'format' : '%.1f', 'width' : 50, 'help' : 'Moyenne de lancers-francs réussis'},
    'FTA' : {'col' : 'num', 'display' : 'FTA', 'format' : '%.1f', 'width' : 50, 'help' : 'Moyenne de lancers-francs tentés'},
    'FT_PCT' : {'col' : 'num', 'display' : 'FT%', 'format' : "%.1f%%", 'width' : 60, 'help' : 'Pourcentage de lancers-francs réussis'},
    'FG2M' : {'col' : 'num', 'display' : 'FG2', 'format' : '%.1f', 'width' : 50, 'help' : 'Moyenne de tirs à 2 pts réussis'},
    'FG2A' : {'col' : 'num', 'display' : 'FG2A', 'format' : '%.1f', 'width' : 50, 'help' : 'Moyenne de tirs à 2 pts tentés'},
    'FG2_PCT' : {'col' : 'num', 'display' : 'FG2%', 'format' : "%.1f%%", 'width' : 60, 'help' : 'Pourcentage de tirs à 2 pts réussis'},
    'EFG_PCT' : {'col' : 'num', 'display' : 'eFG%', 'format' : "%.1f%%", 'width' : 60, 'help' : 'Moyenne aux tirs pondérée qui prend en compte que les tirs à 3 points valent plus'},
    'TS_PCT' : {'col' : 'num', 'display' : 'TS%', 'format' : "%.1f%%", 'width' : 60, 'help' : 'Moyenne aux tirs pondérée pour prendre en compte les 3 points et les lancers francs'},
    
    # TTFL stats
    'avg_team_TTFL' : {'col' : 'num', 'display' : 'TTFL', 'format' : '%.1f', 'width' : 70, 'help' : "Moyenne TTFL de l'équipe"},
    'avg_opp_TTFL' : {'col' : 'num', 'display' : 'TTFL adv.', 'format' : '%.1f', 'width' : 70, 'help' : "Moyenne TTFL des adversaires"},
    'net_TTFL' : {'col' : 'num', 'display' : 'ΔTTFL', 'format' : '%+.1f', 'width' : 70, 'help' : "Différence entre TTFL et TTFL adv."},
    'rel_team_avg_TTFL' : {'col' : 'num', 'display' : 'TTFL%', 'format' : "%+.1f%%", 'width' : 70, 'help' : "Moyenne TTFL de l'équipe par rapport à la moyenne TTFL de toutes les équipes"},
    'rel_opp_avg_TTFL' : {'col' : 'num', 'display' : 'TTFL% adv.', 'format' : "%+.1f%%", 'width' : 85, 'help' : "Moyenne TTFL des adversaires par rapport à la moyenne TTFL de toutes les équipes"},
    'net_rel_TTFL' : {'col' : 'num', 'display' : 'ΔTTFL%', 'format' : '%+.1f', 'width' : 70, 'help' : "Différence entre TTFL% et TTFL% adv."},

    # Opponent stats
    'pts' : {'col' : 'num', 'display' : 'Pts', 'format' : '%.1f', 'width' : 50, 'help' : 'Moyenne de points marqués par les adversaires'},
    'ast' : {'col' : 'num', 'display' : 'Ast', 'format' : '%.1f', 'width' : 42, 'help' : 'Moyenne de passes décisives des adversaires'},
    'reb' : {'col' : 'num', 'display' : 'Reb', 'format' : '%.1f', 'width' : 42, 'help' : 'Moyenne de rebonds pris par les adversaires'},
    'Oreb' : {'col' : 'num', 'display' : 'Oreb', 'format' : '%.1f', 'width' : 42, 'help' : 'Moyenne de rebonds offensifs pris par les adversaires'},
    'Dreb' : {'col' : 'num', 'display' : 'Dreb', 'format' : '%.1f', 'width' : 42, 'help' : 'Moyenne de rebonds défensifs pris par les adversaires'},
    'tov' : {'col' : 'num', 'display' : 'Tov', 'format' : '%.1f', 'width' : 42, 'help' : 'Moyenne de pertes de balles des adversaires'},
    'stl' : {'col' : 'num', 'display' : 'Stl', 'format' : '%.1f', 'width' : 40, 'help' : 'Moyenne d\'interceptions des adversaires'},
    'blk' : {'col' : 'num', 'display' : 'Blk', 'format' : '%.1f', 'width' : 40, 'help' : 'Moyenne de tirs contrés par les adversaires'},
    
    'opp_FGM' : {'col' : 'num', 'display' : 'FG', 'format' : '%.1f', 'width' : 40, 'help' : 'Moyenne de tirs marqués par les adversaires'},
    'opp_FGA' : {'col' : 'num', 'display' : 'FGA', 'format' : '%.1f', 'width' : 40, 'help' : 'Moyenne de tirs tentés par les adversaires'},
    'opp_FG_PCT' : {'col' : 'num', 'display' : 'FG%', 'format' : "%.1f%%", 'width' : 55, 'help' : 'Pourcentage de tirs réussis par les adversaires'},
    'opp_FG3M' : {'col' : 'num', 'display' : 'FG3', 'format' : '%.1f', 'width' : 40, 'help' : 'Moyenne de tirs à 3 points marqués par les adversaires'},
    'opp_FG3A' : {'col' : 'num', 'display' : 'FG3A', 'format' : '%.1f', 'width' : 45, 'help' : 'Moyenne de tirs à 3 points tentés par les adversaires'},
    'opp_FG3_PCT' : {'col' : 'num', 'display' : 'FG3%', 'format' : "%.1f%%", 'width' : 55, 'help' : 'Pourcentage de tirs à 3 pts réussis par les adversaires'},
    'opp_FTM' : {'col' : 'num', 'display' : 'FT', 'format' : '%.1f', 'width' : 40, 'help' : 'Moyenne de lancers-francs réussis par les adversaires'},
    'opp_FTA' : {'col' : 'num', 'display' : 'FTA', 'format' : '%.1f', 'width' : 40, 'help' : 'Moyenne de lancers-francs tentés par les adversaires'},
    'opp_FT_PCT' : {'col' : 'num', 'display' : 'FT%', 'format' : "%.1f%%", 'width' : 55, 'help' : 'Pourcentage de lancers-francs réussis par les adversaires'},

    'opp_EFG' : {'col' : 'num', 'display' : 'eFG%', 'format' : "%.1f%%", 'width' : 55, 'help' : 'Effective Field Goald % des adversaires'},
    'opp_TS' : {'col' : 'num', 'display' : 'TS%', 'format' : "%.1f%%", 'width' : 55, 'help' : 'True Shooting % des adversaires'},
}

PLAYER_STATS_COLUMN_DEF = {
    
    # Regular stats
    'playerName' : {'col' : 'text', 'display' : 'Joueur', 'format' : None, 'width' : 150, 'help' : None},
    'teamTricode' : {'col' : 'text', 'display' : 'Équipe', 'format' : None, 'width' : 50, 'help' : None},
    'opponent' : {'col' : 'text', 'display' : 'Équipe', 'format' : None, 'width' : 50, 'help' : None},
    'GP' : {'col' : 'num', 'display' : 'GP', 'format' : None, 'width' : 35, 'help' : 'Nombre de matchs joués'},
    'Pts' : {'col' : 'num', 'display' : 'Pts', 'format' : '%.1f', 'width' : 35, 'help' : 'Moyenne de points marqués'},
    'Ast' : {'col' : 'num', 'display' : 'Ast', 'format' : '%.1f', 'width' : 35, 'help' : 'Moyenne de passes décisives'},
    'Reb' : {'col' : 'num', 'display' : 'Reb', 'format' : '%.1f', 'width' : 35, 'help' : 'Moyenne de rebonds'},
    'Oreb' : {'col' : 'num', 'display' : 'Oreb', 'format' : '%.1f', 'width' : 35, 'help' : 'Moyenne de rebonds offensifs'},
    'Dreb' : {'col' : 'num', 'display' : 'Dreb', 'format' : '%.1f', 'width' : 35, 'help' : 'Moyenne de rebonds défensifs'},
    'Stl' : {'col' : 'num', 'display' : 'Stl', 'format' : '%.1f', 'width' : 35, 'help' : 'Moyenne d\'interceptions'},
    'Blk' : {'col' : 'num', 'display' : 'Blk', 'format' : '%.1f', 'width' : 35, 'help' : 'Moyenne de tirs contrés'},
    'Tov' : {'col' : 'num', 'display' : 'Tov', 'format' : '%.1f', 'width' : 35, 'help' : 'Moyenne de balles perdues'},
    'Stk' : {'col' : 'num', 'display' : 'Stk', 'format' : '%.1f', 'width' : 35, 'help' : 'Stocks : steals + blocks'},
    'TTFL' : {'col' : 'num', 'display' : 'TTFL', 'format' : '%.1f', 'width' : 35, 'help' : 'Moyenne TTFL'},
    'ttfl_per_min' : {'col' : 'num', 'display' : 'TTFL/min', 'format' : '%.2f', 'width' : 70, 'help' : 'Moyenne TTFL par minute'},
    'PM' : {'col' : 'num', 'display' : '±', 'format' : '%+.1f', 'width' : 40, 'help' : 'Plus/minus'},

    'TOT_Pts' : {'col' : 'num', 'display' : 'Pts', 'format' : '%.0f', 'width' : 35, 'help' : 'Total de points marqués'},
    'TOT_Ast' : {'col' : 'num', 'display' : 'Ast', 'format' : '%.0f', 'width' : 35, 'help' : 'Total de passes décisives'},
    'TOT_Reb' : {'col' : 'num', 'display' : 'Reb', 'format' : '%.0f', 'width' : 35, 'help' : 'Total de rebonds'},
    'TOT_Oreb' : {'col' : 'num', 'display' : 'Oreb', 'format' : '%.0f', 'width' : 35, 'help' : 'Total de rebonds offensifs'},
    'TOT_Dreb' : {'col' : 'num', 'display' : 'Dreb', 'format' : '%.0f', 'width' : 35, 'help' : 'Total de rebonds défensifs'},
    'TOT_Stl' : {'col' : 'num', 'display' : 'Stl', 'format' : '%.0f', 'width' : 35, 'help' : 'Total d\'interceptions'},
    'TOT_Blk' : {'col' : 'num', 'display' : 'Blk', 'format' : '%.0f', 'width' : 35, 'help' : 'Total de tirs contrés'},
    'TOT_Tov' : {'col' : 'num', 'display' : 'Tov', 'format' : '%.0f', 'width' : 35, 'help' : 'Total de balles perdues'},
    'TOT_Stk' : {'col' : 'num', 'display' : 'Stk', 'format' : '%.0f', 'width' : 35, 'help' : 'Total : steals + blocks'},
    'TOT_TTFL' : {'col' : 'num', 'display' : 'TTFL', 'format' : '%.0f', 'width' : 35, 'help' : 'Total TTFL'},
    'TOT_PM' : {'col' : 'num', 'display' : '±', 'format' : '%+.0f', 'width' : 40, 'help' : 'Plus/minus cumulé'},
    'TOT_MINUTES' : {'col' : 'text', 'display' : 'Min', 'format' : None, 'width' : 45, 'help' : 'Total de minutes jouées'},

    # Advanced stats
    'ast_to_tov' : {'col' : 'num', 'display' : 'Ast/tov', 'format' : '%.2f', 'width' : 60, 'help' : 'Moyenne de passes décisives divisée par la moyenne de balles perdues'},
    'FG3_ratio' : {'col' : 'num', 'display' : 'Ratio 3pts', 'format' : "%.1f%%", 'width' : 60, 'help' : 'Pourcentage de tirs tentés qui sont des 3 pts'},
    'MINUTES' : {'col' : 'text', 'display' : 'Min', 'format' : None, 'width' : 45, 'help' : 'Moyenne de minutes jouées par match'},
    'EFG' : {'col' : 'num', 'display' : 'eFG%', 'format' : "%.1f%%", 'width' : 50, 'help' : 'Moyenne aux tirs pondérée qui prend en compte que les tirs à 3 points valent plus'},
    'TS' : {'col' : 'num', 'display' : 'TS%', 'format' : "%.1f%%", 'width' : 50, 'help' : 'Moyenne aux tirs pondérée pour prendre en compte les 3 points et les lancers francs'},

    # Shooting stats
    'FGM' : {'col' : 'num', 'display' : 'FG', 'format' : '%.1f', 'width' : 40, 'help' : 'Moyenne de tirs marqués'},
    'FGA' : {'col' : 'num', 'display' : 'FGA', 'format' : '%.1f', 'width' : 40, 'help' : 'Moyenne de tirs tentés'},
    'FG_PCT' : {'col' : 'num', 'display' : 'FG%', 'format' : "%.1f%%", 'width' : 50, 'help' : 'Pourcentage de tirs réussis'},
    'FG3M' : {'col' : 'num', 'display' : 'FG3', 'format' : '%.1f', 'width' : 40, 'help' : 'Moyenne de tirs à 3 points marqués'},
    'FG3A' : {'col' : 'num', 'display' : 'FG3A', 'format' : '%.1f', 'width' : 40, 'help' : 'Moyenne de tirs à 3 points tentés'},
    'FG3_PCT' : {'col' : 'num', 'display' : 'FG3%', 'format' : "%.1f%%", 'width' : 50, 'help' : 'Pourcentage de tirs à 3 pts réussis'},
    'FTM' : {'col' : 'num', 'display' : 'FT', 'format' : '%.1f', 'width' : 35, 'help' : 'Moyenne de lancers-francs réussis'},
    'FTA' : {'col' : 'num', 'display' : 'FTA', 'format' : '%.1f', 'width' : 35, 'help' : 'Moyenne de lancers-francs tentés'},
    'FT_PCT' : {'col' : 'num', 'display' : 'FT%', 'format' : "%.1f%%", 'width' : 50, 'help' : 'Pourcentage de lancers-francs réussis'},
    'FG2M' : {'col' : 'num', 'display' : 'FG2', 'format' : '%.1f', 'width' : 40, 'help' : 'Moyenne de tirs à 2 pts réussis'},
    'FG2A' : {'col' : 'num', 'display' : 'FG2A', 'format' : '%.1f', 'width' : 40, 'help' : 'Moyenne de tirs à 2 pts tentés'},
    'FG2_PCT' : {'col' : 'num', 'display' : 'FG2%', 'format' : "%.1f%%", 'width' : 50, 'help' : 'Pourcentage de tirs à 2 pts réussis'},

    'TOT_FGM' : {'col' : 'num', 'display' : 'FG', 'format' : '%.0f', 'width' : 40, 'help' : 'Total de tirs marqués'},
    'TOT_FGA' : {'col' : 'num', 'display' : 'FGA', 'format' : '%.0f', 'width' : 40, 'help' : 'Total de tirs tentés'},
    'TOT_FG3M' : {'col' : 'num', 'display' : 'FG3', 'format' : '%.0f', 'width' : 40, 'help' : 'Total de tirs à 3 points marqués'},
    'TOT_FG3A' : {'col' : 'num', 'display' : 'FG3A', 'format' : '%.0f', 'width' : 40, 'help' : 'Total de tirs à 3 points tentés'},
    'TOT_FTM' : {'col' : 'num', 'display' : 'FT', 'format' : '%.0f', 'width' : 40, 'help' : 'Total de lancers-francs réussis'},
    'TOT_FTA' : {'col' : 'num', 'display' : 'FTA', 'format' : '%.0f', 'width' : 40, 'help' : 'Total de lancers-francs tentés'},
    'TOT_FG2M' : {'col' : 'num', 'display' : 'FG2', 'format' : '%.0f', 'width' : 40, 'help' : 'Total de tirs à 2 pts réussis'},
    'TOT_FG2A' : {'col' : 'num', 'display' : 'FG2A', 'format' : '%.0f', 'width' : 40, 'help' : 'Total de tirs à 2 pts tentés'},

    # TTFL stats
    'TTFL' : {'col' : 'num', 'display' : 'TTFL', 'format' : '%.1f', 'width' : 35, 'help' : 'Moyenne TTFL'},
    'max_ttfl' : {'col' : 'num', 'display' : 'Max', 'format' : '%.0f', 'width' : 35, 'help' : 'Score TTFL maximum'},
    'min_ttfl' : {'col' : 'num', 'display' : 'Min', 'format' : '%.0f', 'width' : 35, 'help' : 'Score TTFL minimum'},
    'median_TTFL' : {'col' : 'num', 'display' : 'Médiane', 'format' : '%.1f', 'width' : 35, 'help' : 'Médiane TTFL'},
    'stddev_TTFL' : {'col' : 'num', 'display' : 'Ecart-type', 'format' : '%.1f', 'width' : 45, 'help' : 'Écart-type TTFL'},
    'home_avg_TTFL' : {'col' : 'num', 'display' : 'Home', 'format' : '%.1f', 'width' : 35, 'help' : 'Moyenne TTFL à la maison'},
    'away_avg_TTFL' : {'col' : 'num', 'display' : 'Away', 'format' : '%.1f', 'width' : 35, 'help' : 'Moyenne TTFL à l\'extérieur'},
    'home_rel_TTFL' : {'col' : 'num', 'display' : 'Home%', 'format' : "%+.1f%%", 'width' : 50, 'help' : 'Variation de la moyenne TTFL à la maison'},
    'away_rel_TTFL' : {'col' : 'num', 'display' : 'Away%', 'format' : "%+.1f%%", 'width' : 50, 'help' : 'Variation de la moyenne TTFL à l\'extérieur'},
    'btbTTFL' : {'col' : 'num', 'display' : 'B2B', 'format' : '%.1f', 'width' : 35, 'help' : 'Moyenne TTFL en back to back'},
    'n_btb' : {'col' : 'num', 'display' : 'Nb. B2B', 'format' : '%.0f', 'width' : 35, 'help' : 'Nombre de matchs en back to back'},
    'rel_btb_TTFL' : {'col' : 'num', 'display' : 'B2B%', 'format' : "%+.1f%%", 'width' : 50, 'help' : 'Variation de la moyenne TTFL en back to back'},
}