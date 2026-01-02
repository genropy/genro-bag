
# 02 — Path Syntax (Complete)

## 1. Introduction
Path syntax enables navigation through the RHB without raising exceptions.

## 2. Segment Types

### 2.1 Label
```
aaa.bbb.ccc
```

### 2.2 Position Index `#N`
Select child by insertion order:
```
aaa.#2
```
N is 0-based.

### 2.3 Parent Navigation `/parent`
```
aaa.bbb.ccc/parent
aaa.bbb.ccc/parent/parent
```

### 2.4 Attribute Access `?attr`
```
aaa.bbb.ccc?color
```

## 3. Grammar

```
path          = segment { "." segment } [ attribute ] ;
segment       = label | index | parent ;
label         = /[A-Za-z0-9_]+/ ;
index         = "#" integer ;
parent        = "/parent" ;
attribute     = "?" label ;
```

## 4. Rules

- **getitem never raises**, returns None/default.
- **setItem requires final segment = label**.
- `#N` allowed for selection, **not for insertion**.
- `/parent` may move above root → returns None.
- `?attr` returns attribute value or default.

## 5. Examples

```
aaa.#2.beta?ccc
root.items.#0.properties.color
aaa.bbb.#4/parent?status
```
