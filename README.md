# Projet Data Engineering: Analyse des tweets des lignes de métros et RER parisiens  

## Description du projet  

Le projet consiste à collecter des données à partir des comptes Twitter des lignes de métros/RER de la RATP, en utilisant des techniques de scrapping, à nettoyer et traiter ces données, puis à les analyser à l'aide d'Elascticsearch et de Kibana. Le but dans ce projet est d'obtenir des informations utiles à partir des données collectées et ainsi mettre en avant quelles sont les lignes les plus ou moins fiables.  

## Guide d'utilisation

L'environnement: `Python 3.9`  

Cloner le dépot git:  
Avec SSH: `git@github.com:Alej33/Projet_DataEngineering.git`  
Avec HTTPS: `https://github.com/Alej33/Projet_DataEngineering.git`  

Lancez le container Docker avec le fichier docker-compose:  
```cmd
>docker-compose up -d
```

Lancez ensuite l'application flask:
```cmd
>set FLASK_APP=main
>flask run
```
Puis allez sur le lien http://127.0.0.1:5000/templates pour accéder au dashboard.  

## Guide développeur

### Scraping  

Afin de scraper les comptes twitter des différentes lignes de la RATP, il existe 2 moyens. Soit en passant par l'API twitter, pour cela on doit faire une demande à partir du site de développeur de Twitter et on a une réponse sous quelques jours. Pour mon cas, la demande a été très fastidieuse vu qu'il demandait de répondre à des questions supplémentaires concernant l'utilisation de l'API par mail, et après avoir répondu, les réponses ne leurs convenait pas et donc demander encore plus de question (qui été parfois les mêmes questions).  
De plus, depuis le 9 février, l'API Twitter est devenue payante et donc inutilisable pour le scraping.  

J'ai donc opter pour le 2ème moyen qui est un scraping plus 'classique'. Vu que Twitter utilise une pagination dynamique, le package Selenium serait approprié, mais pour le projet ce ne serait pas optimal vu qu'on veut scraper plusieurs comptes Twitter. On utilise donc le package `snscrape` qui permet un scraping simple des comptes Twitter.  

Le scraping a été fait dans le fichier `scraping.ipynb`. Ce qu'on va scraper est l'ensemble des lignes de métros, RER et Trams. On va y collecter les noms d'utilisateur Twitter, les tweets et les dates des tweets. En utilisant la documentation de snscrape, voici comment on extrait ces informations:
```python
tweet.rawContent  #tweets
tweet.date  #Date
tweet.user.username  #Nom d'utilisateur
```
On y collectera les 2000 premiers tweets de chaque compte de métros et RER. Et seulement 500 tweets pour les trams (vu qu'il y a moins de tweets pour les trams). Pour ne pas se retrouver avec pleins de tweets inutiles, on met une condition pour ne pas inclure les réponses.  
On met ensuite ces données dans une dataframe pandas.  

### Nettoyage et traitement des données

Après avoir collectés les tweets de manière brute, on fait un nettoyage pour mieux traiter ces tweets:  

- On formate les dates des tweets pour que cela soit en deux colonnes avec date et heures séparées.
- On enlève les retour à la ligne ('\n'), les emojis, les hastags et les liens internet.
- On garde seulement les tweets qui concernent les problèmes sur la ligne et on enlève les tweets qui concernent un rétablissement de la ligne.  

Le but dans ce nettoyage, c'est de pouvoir travailler que sur des tweets qui concernent sur des problèmes sur la ligne (même si certains ne sont pas correctement filtrés).  
Pour le traitement, on s'aidera du module Kibana pour avoir une vue d'ensemble des tweets, le traitement a été faite dans le fichier `processing.ipynb`.  
Ce qu'on veut maintenant, c'est de pouvoir extraire la raison de perturbation pour chaque tweets. Pour cela, on remarquera que chaque raison est précédé de certains mots: `(raison|cause|origine|suite|répercussion)`. On remarquera ensuite que les tweets les plus anciens, les raisons des perturbations sont soit entre parenthèses ou soit entre crochet.  
Grâce aux expressions régulière, on peut donc ainsi extraire les raisons en question. Mais cela ne reste pas parfait. En effet, le premier problème c'est qu'on se retrouve avec des phrases complètes dans la colonne raison, malgré qu'on ait fait une condition pour couper la phrase à partir d'un point ou une virgule.  
De plus, il y'a beaucoup d'informations entre parenthèses qui ne sont pas pertinentes. On essaye de se débarraser des valeurs assez fréquentes comme les valeurs sous la forme [chiffre/chiffre] et les 'Port du masque' qui se retrouvait souvent entre crochet.  
Cependant, la colonne raison reste ne toujours pas exploitable, on veut donc extraire les mots-clés, la réelle raison de la perturbations. Pour cela on utilise le package `nltk` qui une bibliothèque python qui permet de faire du traitement automatique du langage.  

```python
reasons = list(df_problemes['raison'])
stopwords = list(fr_stop) + ["d'un","d'une", ',', '’', 'd', 'l', ')','(', 'train', 'station', 'trafic', 'perturbé', '*', "'"]
all_reasons = ' '.join(reasons)
tokens = word_tokenize(all_reasons)
tokens_without_stopwords = [word for word in tokens if word.lower() not in stopwords]
freq = FreqDist(tokens_without_stopwords)

#Extraction des raisons les plus fréquentes
most_common_reasons = [word for word, count in freq.most_common(100)]
```
Dans ce bloc de code, on compte les mots les plus fréquents de la colonne raison, en excluant les stopword. La liste des stopswords est fournie par le package `Spacy` qui est aussi une bibliothèque python permettant de faire du traitement du langage automatique, il possède une liste de stopwords plus conséquent que nltk en français.  
Pour compter les mots, on tokenise les mots de la colonne 'raison' et on utilise la fonction `FreqDist()` pour savoir la fréquence des mots. On prend ensuite les 100 premiers mots les plus communs.  
On utilise ensuite une boucle pour créer une nouvelle colonne 'raison_keyword'. Pour que les mots-clés des raisons soit plus compréhensible, on rénomme une grand partie d'entre eux.

Je tiens à préciser que cela toujours pas parfait et qu'il y a encore des tweets qui ne sont pas correctement filtrés mais on a maintenant un dataset exploitable. On passe ensuite sur Kibana pour y faire des graphiques et un dashboard.

### Application Flask

L'application Flask va permettre d'afficher le dashboard qui a été créer sur Kibana. Le dashboard en question est intégré dans une page HTML grâce à une iframe.  
Or pour faire fonctionner ce dashboard, il faut indexer les données dans Elasticsearch et importer les objets Kibana qui sont sous la forme de fichier .ndjson. 

C'est pour cela qu'on retrouve dans le fichier `main.py` une fonction `index_data(es, index_name, data)` pour indexer les données dans Elasticsearch et une fonction `import_index_dashboard()` pour importer les objets Kibana, qui contiennent l'index pattern et le dashboard.  
La fonction `import_index_dashboard()` utilise la fonction `os.system()` qui permet d'intéragir avec le terminal windows.  
En effet, pour pouvoir importer les objets Kibana qui sont sous la forme d'un fichier .ndjson, une commande spécifique qui fait appel à l'API de Kibana:
```cmd
>cmd /c "curl -X POST "localhost:5601/api/saved_objects/_import" -H "kbn-xsrf: true" --form file=@export_index_pattern.ndjson
>cmd /c "curl -X POST "localhost:5601/api/saved_objects/_import" -H "kbn-xsrf: true" --form file=@export_dashboard.ndjson
```
Si tout se passe bien, on devrait voir le dashboard Kibana. 

## Rapport d'analyse

Dans ce dashboard, différents graphiques ont été faits. Voici une bref conclusion qui peuvent être en tirer:

- Le bagage oublié est la perturbation la plus fréquente sur l'ensemble du réseaux francilien, il est suivi par incident technique/voyageur, panne de signalisation/train et malaise voyageur.
- Le RER A est la ligne qui a le plus de perturbations, il est suivi par le RER B.
- Les lignes 7, 8 et 13 sont les 3 lignes de métros les plus pertubées.  
- On recense environ 12000 incidents en 3 ans sur l'ensemble du réseaux francilien.
- On remarquera le peu d'incident durant l'année 2020, cela peut s'expliquer par la pandémie du Covid-19.
