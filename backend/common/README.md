# Shared Backend Components

`common.models` provides UUID primary keys and append-only ORM behavior for event/history records. Domain-specific validation and relationships remain in their owning Django apps. Append-only ORM checks are a protection against ordinary Django writes; database-role privileges and operational controls are still required for stronger audit protection.
