# Flutter Provider learning material

This small standalone project is the authorized test material for the overnight Tutor sprint. It contains no personal course files. Run `flutter pub get` then `flutter test` here.

The lesson is `lib/main.dart`. `Counter` owns the data. `ChangeNotifierProvider` creates and exposes it below the provider. `CounterPage.build` watches it. The button callback reads the same object and increments it; `notifyListeners` notifies subscribed consumers. Rebuilding a widget does not mean recreating every element or rendering the entire application.

Independent reviewer references (not injected as standard model answers):

- [Provider package documentation](https://pub.dev/packages/provider)
- [Flutter simple app state management](https://docs.flutter.dev/data-and-backend/state-mgmt/simple)
- [ChangeNotifier API](https://api.flutter.dev/flutter/foundation/ChangeNotifier-class.html)

Distinguish this Provider package from Riverpod. `context.read` does not subscribe to changes; use it in the callback. `context.watch` in `build` establishes a dependency. Removing `notifyListeners` prevents this state change from notifying the listener, though an unrelated rebuild can still reveal the changed value. A `const` widget can depend on inherited state and still rebuild.
