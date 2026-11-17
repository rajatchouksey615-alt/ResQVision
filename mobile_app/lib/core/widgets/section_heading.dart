import 'package:flutter/material.dart';

class SectionHeading extends StatelessWidget {
  const SectionHeading({super.key, required this.title, this.description});

  final String title;
  final String? description;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        Text(title, style: Theme.of(context).textTheme.titleLarge),
        if (description != null) ...<Widget>[
          const SizedBox(height: 4),
          Text(description!, style: Theme.of(context).textTheme.bodyMedium),
        ],
      ],
    );
  }
}
