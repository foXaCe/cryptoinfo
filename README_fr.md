## Composant de capteurs Home Assistant pour les cryptomonnaies
[![hacs_badge](https://img.shields.io/badge/HACS-Default-orange.svg)](https://github.com/hacs/integration)

![icon_mini](https://github.com/user-attachments/assets/328f93d8-6ea7-4877-bc31-1c5b33c4583a)
### Propulsé par l'API CoinGecko

#### Fournit des capteurs Home Assistant pour toutes les cryptomonnaies supportées par CoinGecko

## Changements majeurs pour la mise à jour de v0.x.x vers v1.x.x
Si vous venez de mettre à jour de v0.x.x vers v1.x.x, veuillez supprimer le capteur cryptoinfo de votre configuration.yaml et suivre [Étape d'installation 2](#étape-dinstallation-2)

Si vous appréciez mon travail, offrez-moi un café ou faites un don en cryptomonnaies. Cela me gardera éveillé, endormi, ou je ne sais quoi :wink:

<a href="https://www.buymeacoffee.com/1v3ckWD" target="_blank"><img src="https://www.buymeacoffee.com/assets/img/custom_images/orange_img.png"></a><details>
  <summary>Adresses de cryptomonnaies</summary>
<img width="164px" alt="xmr" src="https://user-images.githubusercontent.com/20553716/210132784-63613225-d9da-427d-a20b-e1003045a1f4.png">
<img width="164px" alt="btc" src="https://user-images.githubusercontent.com/20553716/210132426-6c58d8d1-b351-4ae7-9b61-cd5511cdb4ed.png">
<img width="164px" alt="ada" src="https://user-images.githubusercontent.com/20553716/210132510-b1106b55-c9e3-413d-b8e0-26ba4e24a5de.png">
</details>

Si vous avez besoin de fonctionnalités plus avancées que celles offertes par ce projet, consultez [Cryptoinfo Advanced](https://github.com/TheHolyRoger/hass-cryptoinfo)

### Étape d'installation 1 :
Il y a 2 façons d'installer cryptoinfo :
1. Téléchargez 'cryptoinfo' depuis le magasin HACS
2. Copiez les fichiers du dossier /custom_components/cryptoinfo/ vers : [homeassistant]/config/custom_components/cryptoinfo/

### Étape d'installation 2
L'étape suivante consiste à ajouter des capteurs cryptoinfo à votre Home Assistant :
1. Accédez à votre page de configuration Home Assistant
2. Cliquez sur Paramètres --> Appareils et Services

![image](https://github.com/user-attachments/assets/c4812206-835e-4239-9757-8645ae6c772b)

3. Cliquez sur 'Ajouter une intégration' et recherchez 'cryptoinfo' puis sélectionnez l'intégration 'cryptoinfo'

![image](https://github.com/user-attachments/assets/83e3e165-61fa-4aa9-8421-9fc019bfae82)

4. Remplissez le formulaire 'ajouter un nouveau capteur'

![image](https://github.com/user-attachments/assets/d76156df-dc2c-4f5f-bbdf-ea58570c5963)

### Propriétés
<pre>
- Identifiant                               Nom unique pour le capteur
- ID de cryptomonnaies                      Une ou plusieurs valeurs 'id' (séparées par une virgule) que vous pouvez trouver sur cette <a href='https://api.coingecko.com/api/v3/coins/list' target='_blank'>page</a>
- Multiplicateurs                           Le nombre de pièces/jetons (séparés par une virgule). Le nombre de multiplicateurs doit correspondre au nombre d'ID de cryptomonnaies
- Nom de la devise                          L'un des noms de devises que vous pouvez trouver sur cette <a href='https://api.coingecko.com/api/v3/simple/supported_vs_currencies' target='_blank'>page</a>
- Unité de mesure                           Vous pouvez utiliser un symbole de devise ou le laisser vide. Vous trouverez certains symboles sur cette <a href='https://en.wikipedia.org/wiki/Currency_symbol#List_of_currency_symbols_currently_in_use' target='_blank'>page</a>
- Fréquence de mise à jour (minutes)        À quelle fréquence la valeur doit-elle être actualisée ? Attention à la <a href='https://support.coingecko.com/hc/en-us/articles/4538771776153-What-is-the-rate-limit-for-CoinGecko-API-public-plan' target='_blank'>limite de taux CoinGecko</a> lors de l'utilisation de plusieurs capteurs
- Temps minimum entre les requêtes (minutes) Le temps minimum entre les autres capteurs et ce capteur pour effectuer une requête de données à l'API. (Cette propriété est partagée et identique pour chaque capteur). Vous pouvez définir cette valeur à 0 si vous n'utilisez qu'un seul capteur
</pre>

### Attributs
Les entités ont des attributs importants :
```
- last_update           Retourne la date et l'heure de la dernière mise à jour
- cryptocurrency_id     Retourne l'ID de la cryptomonnaie
- cryptocurrency_name   Retourne le nom de la cryptomonnaie
- cryptocurrency_symbol Retourne le symbole de la cryptomonnaie
- currency_name         Retourne le nom de la devise
- base_price            Retourne le prix d'une pièce/jeton en 'currency_name' (par défaut = "usd") de la 'cryptocurrency_id'
- multiplier            Retourne le nombre de pièces/jetons
- 24h_volume            Retourne le volume sur 24 heures en 'currency_name' (par défaut = "usd") de la 'cryptocurrency_id' (par défaut = "bitcoin")
- 1h_change             Retourne la variation sur 1 heure en pourcentage de la 'cryptocurrency_id' (par défaut = "bitcoin")
- 24h_change            Retourne la variation sur 24 heures en pourcentage de la 'cryptocurrency_id' (par défaut = "bitcoin")
- 7d_change             Retourne la variation sur 7 jours en pourcentage de la 'cryptocurrency_id' (par défaut = "bitcoin")
- 14d_change            Retourne la variation sur 14 jours en pourcentage de la 'cryptocurrency_id' (par défaut = "bitcoin")
- 30d_change            Retourne la variation sur 30 jours en pourcentage de la 'cryptocurrency_id' (par défaut = "bitcoin")
- 1y_change             Retourne la variation sur 1 an en pourcentage de la 'cryptocurrency_id' (par défaut = "bitcoin")
- market_cap            Retourne la capitalisation boursière totale de la 'cryptocurrency_id' (par défaut = "bitcoin") affichée en 'currency_name' (par défaut = "usd")
- circulating_supply    Retourne l'offre en circulation de la 'cryptocurrency_id' (par défaut = "bitcoin")
- total_supply          Retourne l'offre totale de la 'cryptocurrency_id' (par défaut = "bitcoin")
- ath_price             Retourne le prix le plus élevé de tous les temps (ATH) en 'currency_name' (par défaut = "usd") de la 'cryptocurrency_id' (par défaut = "bitcoin")
- ath_date              Retourne la date à laquelle le prix le plus élevé de tous les temps a été atteint en 'currency_name' (par défaut = "usd") de la 'cryptocurrency_id' (par défaut = "bitcoin")
- ath_change            Retourne le pourcentage de variation par rapport au prix le plus élevé de tous les temps en 'currency_name' (par défaut = "usd") de la 'cryptocurrency_id' (par défaut = "bitcoin")
- rank                  Retourne le classement de la cryptomonnaie
- image                 Retourne l'image de la cryptomonnaie
```

Exemple de template pour l'utilisation des attributs.
Cet exemple crée un nouveau capteur avec la valeur de l'attribut '24h_volume' du capteur 'sensor.cryptoinfo_main_wallet_ethereum_eur' :
```yaml
  - platform: template
    sensors:
      cryptoinfo_main_wallet_ethereum_eur_24h_volume:
        value_template: "{{ state_attr('sensor.cryptoinfo_main_wallet_ethereum_eur', '24h_volume') | float(0) | round(0) }}"
        unit_of_measurement: "€"
```

Si vous voulez connaître la valeur totale de vos cryptomonnaies, vous pouvez utiliser ce template comme exemple.
Cet exemple combine la valeur totale de tous vos capteurs en un seul capteur de template :
```yaml
  - platform: template
    sensors:
      crypto_total:
        value_template: >
          {{ integration_entities('cryptoinfo')
              | map('states')
              | map('float', 0)
              | sum | round(2) }}
        unit_of_measurement: >
          {{ expand(integration_entities('cryptoinfo'))
              | map(attribute='attributes.unit_of_measurement')
              | list | default(['$'], true)
              | first }}
        friendly_name: Valeur totale de toutes mes cryptomonnaies
```

### Limite de l'API
L'API publique de CoinGecko a une <a href='https://support.coingecko.com/hc/en-us/articles/4538771776153-What-is-the-rate-limit-for-CoinGecko-API-public-plan' target='_blank'>limite de taux</a> de 5 à 15 appels par minute, selon les conditions d'utilisation mondiales.

### Problèmes et nouvelles fonctionnalités
S'il y a des problèmes, veuillez créer un ticket dans https://github.com/heyajohnny/cryptoinfo/issues
Si vous souhaitez ajouter de nouvelles fonctionnalités, veuillez créer un ticket avec une description de la nouvelle fonctionnalité souhaitée dans : https://github.com/heyajohnny/cryptoinfo/issues
