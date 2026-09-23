# Migration schema fixtures

These SQL files freeze the exact schema that existed immediately before each migration.

| Fixture | Git source | Schema content hash |
| --- | --- | --- |
| `registry_v1.sql` | commit `e4e1499d181784d68d7edfd5dbe9465d6c372c90` | `7384dfe550093eae0674f1b2acf43050ee0b7841` |
| `registry_v2.sql` | commit `9766210d30e8f7bc887d41fe7589b02a41b4d01a` | `fce9b6f8ad38bf86ab9fd93843a809008427789a` |
| `registry_v3.sql` | tag `1.0.0`, commit `1d3dcc2476f9e1fed7361b27ad8e52b6515b4239` | `e77c092a47d07f880332a5cb127af89271ede238` |
| `ledger_v1.sql` | commit `68a02810e45c957b8df6a7d13d57c7229fd84721` | `30f4323e3083a37e4e06bac25fc6c477946a291b` |

When adding a migration, freeze the exact schema from the version immediately before it and add a dedicated migration test.
