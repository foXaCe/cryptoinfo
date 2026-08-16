# FAQ

## Pourquoi je ne vois pas mon crypto dans la liste des options ?

La liste est basée sur l'API CoinGecko. Vérifiez le nom exact de la cryptomonnaie
(symbole ou identifiant). Certaines cryptos peu liquides peuvent être indisponibles.

## Mes capteurs mettent du temps à se mettre à jour

Le coordonnateur utilise un intervalle de polling configurable. Réduisez-le dans
les options de l'intégration si vous avez besoin d'une réactivité accrue
(attention au rate-limit CoinGecko).

## CoinGecko me rate-limite

L'API gratuite a des quotas. L'intervalle de polling par défaut est choisi pour
respecter les limites. Si vous suivez beaucoup de cryptos, espacez les mises à jour.

## Les capteurs minage Bitcoin ne s'affichent pas

Ils sont créés uniquement si l'API Mempool.space est accessible. Vérifiez la
connectivité réseau vers `mempool.space` depuis votre instance Home Assistant.

## Comment remonter un bug ou proposer une fonctionnalité ?

Ouvrez une issue sur [le dépôt](https://github.com/foXaCe/cryptoinfo/issues)
en utilisant les templates fournis (bug report / feature request).
