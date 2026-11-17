class OrganizationMembership {
  const OrganizationMembership({
    required this.id,
    required this.organizationId,
    required this.organizationCode,
    required this.organizationName,
    required this.organizationKind,
    required this.role,
    required this.status,
    required this.createdAt,
  });

  final String id;
  final String organizationId;
  final String organizationCode;
  final String organizationName;
  final String organizationKind;
  final String role;
  final String status;
  final DateTime createdAt;

  factory OrganizationMembership.fromJson(Object? value) {
    if (value is! Map<String, dynamic>) {
      throw const FormatException('Membership must be an object.');
    }
    return OrganizationMembership(
      id: _requiredString(value, 'id'),
      organizationId: _requiredString(value, 'organization_id'),
      organizationCode: _requiredString(value, 'organization_code'),
      organizationName: _requiredString(value, 'organization_name'),
      organizationKind: _requiredString(value, 'organization_kind'),
      role: _requiredString(value, 'role'),
      status: _requiredString(value, 'status'),
      createdAt: _requiredDate(value, 'created_at'),
    );
  }
}

class AuthenticatedUser {
  const AuthenticatedUser({
    required this.id,
    required this.email,
    required this.firstName,
    required this.lastName,
    required this.roles,
    required this.memberships,
  });

  final String id;
  final String email;
  final String firstName;
  final String lastName;
  final List<String> roles;
  final List<OrganizationMembership> memberships;

  String get displayName {
    final String name = '$firstName $lastName'.trim();
    return name.isEmpty ? email : name;
  }

  List<String> get availableRoles {
    const Set<String> known = <String>{'ADMIN', 'POLICE', 'HOSPITAL'};
    final Set<String> resolved = <String>{
      ...roles.where(known.contains),
      ...memberships
          .where(
            (OrganizationMembership membership) =>
                membership.status == 'ACTIVE',
          )
          .map((OrganizationMembership membership) => membership.role)
          .where(known.contains),
    };
    const List<String> priority = <String>['ADMIN', 'POLICE', 'HOSPITAL'];
    return priority.where(resolved.contains).toList(growable: false);
  }

  factory AuthenticatedUser.fromJson(Object? value) {
    if (value is! Map<String, dynamic>) {
      throw const FormatException('User profile must be an object.');
    }
    final Object? roleValue = value['roles'];
    final Object? membershipsValue = value['memberships'];
    if (roleValue is! List<Object?> || membershipsValue is! List<Object?>) {
      throw const FormatException('User profile collections are invalid.');
    }
    final List<String> roles = roleValue
        .map((Object? role) {
          if (role is! String) {
            throw const FormatException('User role must be text.');
          }
          return role;
        })
        .toList(growable: false);
    return AuthenticatedUser(
      id: _requiredString(value, 'id'),
      email: _requiredString(value, 'email'),
      firstName: _requiredString(value, 'first_name'),
      lastName: _requiredString(value, 'last_name'),
      roles: List<String>.unmodifiable(roles),
      memberships: List<OrganizationMembership>.unmodifiable(
        membershipsValue.map(OrganizationMembership.fromJson),
      ),
    );
  }
}

String _requiredString(Map<String, dynamic> value, String key) {
  final Object? field = value[key];
  if (field is! String) {
    throw FormatException('Profile field $key is invalid.');
  }
  return field;
}

DateTime _requiredDate(Map<String, dynamic> value, String key) {
  final String raw = _requiredString(value, key);
  final DateTime? parsed = DateTime.tryParse(raw);
  if (parsed == null) {
    throw FormatException('Profile field $key is invalid.');
  }
  return parsed;
}
