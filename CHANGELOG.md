# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](http://keepachangelog.com/en/1.0.0/)
and this project adheres to [Semantic Versioning](http://semver.org/spec/v2.0.0.html).

## [0.3.0]
### Changed
- Groups have to be created / deleted explicitly from now on by using the module without `user` property.
  `user` and `group` together are just used for group assignment. Examples are provided in the README (#13) (#14)
- Fix: do not use camelCase variables in README (#12)

## [0.2.0]
### Added
- `update_password` flag to only set user password on_create (#3)

### Changed
- Fix: Create group with a separated statement (#6)
- Fix: Set user privileges without implicitly removing the user from a group (#9)


## [0.1.0]
### Added
- Create / delete users and groups
- Associate user with group
- First draft of privileges support