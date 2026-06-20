# План дополнения Этапа 1.3: Lifecycle, immutability, safe delete

> Утверждено пользователем 2026-06-09. Фаза B — инструкции и контракты обновлены.

## 1. Immutability после старта

После первого `activate` (`is_locked=true`):

- **Запрещено** любое изменение `contest_settings` и `rules_json` (очки, бонусы, структура, участники, команды).
- `PATCH /admin/contest-settings` → **403** при `is_locked`.
- Никаких whitelist-исключений в `rules_json`.

## 2. Exceptional tie-break (не правила)

- Колонка `users.exceptional_tiebreak_points` (default 0).
- ADMIN вписывает очки для редкого случая полного равенства критериев 1–4.
- Критерий 5: `exceptional_tiebreak_points DESC`.
- Разрешено **даже при** `is_locked` — это операционные данные, не правила конкурса.
- Эндпоинт: `PUT /admin/users/{user_id}/exceptional-tiebreak`.

## 3. Lifecycle (Option B)

`DRAFT → RUNNING → PAUSED ↔ RUNNING → FINISHED`

- Safe delete: `POST pause` → grace (`contest_delete_grace_seconds=10`) → `DELETE` + `{confirm:"DELETE"}`.
- CI bypass: `contest_allow_instant_delete=true`.

## 4. Порядок

1.2.1 migration → 1.3 API + services → tester_1.3

## 5. Out of scope

Newsletters, background tasks, participant CRUD.
