# Bag Async Problem - Appunti

**Data**: 2026-01-02
**Status**: DA DISCUTERE

## Contesto

La Bag non è thread-safe (ogni thread ha la sua Bag). Il problema multithread con Gunicorn non esiste.

Rimane il problema di come gestire sync/async in modo pulito.

## Casi d'uso previsti

### Caso 1: Sync esterno
```python
result = bag['aaa.bbb.ccc']
```
- L'utente non sa e non vuole sapere se dentro ci sono resolver async
- Deve essere trasparente
- `@smartasync` gestisce questo: da sync fa `asyncio.run()` sulla coroutine

### Caso 2: Async esterno
```python
result = await bag.get_item('aaa.bbb.ccc')
```
- L'utente è in contesto async
- Vuole usare `await` esplicito
- Il lock (`asyncio.Lock`) funziona correttamente in questo contesto

## Problema attuale

Il caso 1 funziona grazie a `@smartasync` su `_resolve_cached`.

Il caso 2 ha problemi:
- La bag non ha un metodo `get_item` async
- Internamente `_htraverse` chiama `resolver()` che in async ritorna una coroutine
- Ma `_htraverse` non è async, quindi non può fare `await`

## Possibili soluzioni discusse

### Opzione A: `_htraverse` con `@smartasync`

`_htraverse` diventa async con `@smartasync`:
- Da sync: `smartasync` fa `asyncio.run()` su tutto il traversal
- Da async: ritorna coroutine, il chiamante fa `await`

Internamente `_htraverse` farebbe `await resolver()` quando incontra un resolver.

**Pro**: API unificata
**Contro**: Tutto il traversal diventa async

### Opzione B: Due metodi separati

- `bag['path']` → sync, usa `_htraverse` sync
- `await bag.get_item('path')` → async, usa `_htraverse_async`

**Pro**: Separazione netta
**Contro**: Duplicazione codice

### Opzione C: Resolver ritorna sempre coroutine

Il resolver ritorna sempre una coroutine. `_htraverse` non fa mai `await` espliciti, ma il decoratore `@smartasync` su `_htraverse` gestisce tutto.

**Pro**: Logica uniforme interna
**Contro**: Da verificare se funziona con path traversal multiplo

## Domande aperte

1. Come gestire il traversal quando ci sono più resolver nel path?
   Es: `bag['aaa.bbb.ccc']` dove sia `aaa` che `bbb` hanno resolver

2. Il lock è necessario solo per `read_only=False`. Per `read_only=True` non serve concurrency control.

3. `SmartLock` attuale usa solo `asyncio.Lock()`. Funziona in async context ma in sync context (con `asyncio.run()`) ogni chiamata crea un nuovo event loop, quindi il lock non protegge nulla tra chiamate sync diverse.

## Decisione

**DA PRENDERE** - L'utente deve pensarci.
