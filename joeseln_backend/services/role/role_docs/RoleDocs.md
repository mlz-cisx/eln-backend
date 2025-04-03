### How User Roles are updated

The hierarchy GUEST < USER < GROUPADMIN < ADMIN within GROUPS semantically
maps the Linux rights system.

#### OIDC USERS

- Carrying user groups create a group if one doesn't already exist and add the
  user with the USER role to that group if they don't already have it.
  It also removes the GUEST role if the user was manually assigned as GUEST.
- Once the USER role has been added to a group, it cannot be manually removed.
- If a user group no longer exists, the user will be removed as a USER and
  GROUPADMIN.
  They can be manually re-added to this group as a GUEST.

#### NON OIDC USERS

- Non-OIDC users can be manually added as USER and then be promoted to
  GROUPADMIN.
- If added as USER in a group the GUEST role will be removed.
- Only non-OIDC Users can be promoted to ADMIN.

#### GENERAL

- Users can only be added as GUEST to a group if they do not have any other role
  in this
  group.
- Users with role USER can be promoted to GROUPADMIN.
- Only empty groups can be deleted.
- (Soft) Deleting a user deletes all of their group roles.
  
  ````
         │                           
         │ Manual Manage             
    ┌────┴────┐                      
    │         │                      
    │         │                      
    ▼         ▼    Manual            
                  Promote            
  Guest      User ───────► Groupadmin
                                     
               ▲                     
               │                     
               │ External            
               │   Managed           
               ▼                     
                                     
             Keycloak                
               Roles

  ````
  
