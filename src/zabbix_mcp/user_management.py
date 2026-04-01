"""
User and role management for Zabbix API.
Provides tools for creating users, managing roles, and checking permissions.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from .client import ZabbixClient


class UserManagement:
    """Zabbix user and role management"""
    
    def __init__(self, client: ZabbixClient):
        self.client = client

    @staticmethod
    def _validate_password(password: str, username: Optional[str], surname: Optional[str] = None) -> List[str]:
        """Validate password quality and forbidden substrings."""
        validation_errors: List[str] = []
        if len(password) < 8:
            validation_errors.append("Password must be at least 8 characters long")
        if not re.search(r"\d", password):
            validation_errors.append("Password must contain at least one number")
        if not re.search(r"[^A-Za-z0-9]", password):
            validation_errors.append("Password must contain at least one special character")
        if username and username.lower() in password.lower():
            validation_errors.append("Password cannot contain username")
        if surname and surname.lower() in password.lower():
            validation_errors.append("Password cannot contain surname")
        return validation_errors
    
    def create_user(
        self,
        username: str,
        password: str,
        role: str = "Super admin role",
        email: Optional[str] = None,
        name: Optional[str] = None,
        surname: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a new Zabbix user.
        
        Args:
            username: Unique username
            password: User password (cannot contain username/surname)
            role: Role name or ID (default: "Super admin role")
            email: Optional email address
            name: Optional first name
            surname: Optional last name
        
        Returns:
            Dict with:
                - success: bool
                - userid: str (new user ID if created)
                - message: str
                - validation_errors: list (if any)
        
        Validations:
            - Password cannot contain username
            - Password cannot contain surname (if provided)
            - Role must exist in Zabbix
            - Username must be unique
        """
        validation_errors = self._validate_password(password, username, surname)
        
        if validation_errors:
            return {
                "success": False,
                "userid": None,
                "message": "Password validation failed",
                "validation_errors": validation_errors
            }
        
        # Resolve role ID
        role_id = self._resolve_role_id(role)
        if not role_id:
            return {
                "success": False,
                "userid": None,
                "message": f"Role not found: {role}",
                "validation_errors": [f"Unknown role: {role}"]
            }
        
        try:
            # Create user via API
            params = {
                "username": username,
                "passwd": password,
                "roleid": role_id
            }
            
            # Add optional fields
            if email:
                params["usrgrps"] = self._get_user_groups_by_email(email)
            if name:
                params["name"] = name
            if surname:
                params["surname"] = surname
            
            result = self.client.api_call("user.create", params)
            
            if result and "userids" in result:
                userid = result["userids"][0]
                return {
                    "success": True,
                    "userid": userid,
                    "message": f"User created successfully: {username}",
                    "validation_errors": []
                }
            else:
                return {
                    "success": False,
                    "userid": None,
                    "message": "Failed to create user",
                    "validation_errors": ["API returned no user ID"]
                }
        
        except Exception as e:
            return {
                "success": False,
                "userid": None,
                "message": f"Error creating user: {str(e)}",
                "validation_errors": [str(e)]
            }
    
    def update_user(
        self,
        userid: str,
        password: Optional[str] = None,
        roleid: Optional[str] = None,
        current_password: Optional[str] = None,
        email: Optional[str] = None,
        name: Optional[str] = None,
        surname: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Update user properties.
        
        Args:
            userid: User ID to update
            password: New password (requires current_password)
            roleid: New role ID
            current_password: Current password (required if changing password)
            email: New email
            name: New first name
            surname: New surname
        
        Returns:
            Dict with:
                - success: bool
                - message: str
                - changes_made: list (what was changed)
        """
        changes = []
        params = {"userid": userid}
        
        try:
            # Get current user to check username/surname for password validation
            current_user = self.client.api_call("user.get", {
                "output": ["userid", "username", "surname"],
                "userids": userid
            })
            
            if not current_user:
                return {
                    "success": False,
                    "message": f"User not found: {userid}",
                    "changes_made": []
                }
            
            current = current_user[0]
            username = current.get("username")
            current_surname = current.get("surname")
            
            # Update password if provided
            if password:
                if not current_password:
                    return {
                        "success": False,
                        "message": "current_password required when changing password",
                        "changes_made": []
                    }
                
                # Validate new password
                if not username:
                    return {
                        "success": False,
                        "message": "Cannot validate password without username",
                        "changes_made": []
                    }

                password_errors = self._validate_password(password, username, current_surname)
                if password_errors:
                    return {
                        "success": False,
                        "message": f"New password validation failed: {', '.join(password_errors)}",
                        "changes_made": []
                    }
                
                params["passwd"] = password
                params["current_passwd"] = current_password
                changes.append("password")
            
            # Update role if provided
            if roleid:
                params["roleid"] = roleid
                changes.append("role")
            
            # Update other fields
            if email:
                params["email"] = email
                changes.append("email")
            if name:
                params["name"] = name
                changes.append("name")
            if surname:
                params["surname"] = surname
                changes.append("surname")
            
            if len(params) == 1:  # Only userid
                return {
                    "success": True,
                    "message": "No changes requested",
                    "changes_made": []
                }
            
            result = self.client.api_call("user.update", params)
            
            if result and "userids" in result:
                return {
                    "success": True,
                    "message": "User updated successfully",
                    "changes_made": changes
                }
            else:
                return {
                    "success": False,
                    "message": "Failed to update user",
                    "changes_made": []
                }
        
        except Exception as e:
            return {
                "success": False,
                "message": f"Error updating user: {str(e)}",
                "changes_made": []
            }
    
    def get_roles(self) -> Dict[str, Any]:
        """
        Get list of all available roles.
        
        Returns:
            Dict with:
                - roles: list of dicts with roleid and name
                - total: int
        """
        try:
            roles = self.client.api_call("role.get", {
                "output": ["roleid", "name", "type"]
            })
            
            return {
                "roles": roles or [],
                "total": len(roles) if roles else 0
            }
        except Exception as e:
            return {
                "roles": [],
                "total": 0,
                "error": str(e)
            }
    
    def assign_role_to_user(self, userid: str, roleid: str) -> Dict[str, Any]:
        """
        Assign role to user.
        
        Args:
            userid: User ID
            roleid: Role ID
        
        Returns:
            Dict with success status and message
        """
        try:
            result = self.client.api_call("user.update", {
                "userid": userid,
                "roleid": roleid
            })
            
            if result and "userids" in result:
                return {
                    "success": True,
                    "message": f"Role assigned to user {userid}",
                    "userid": userid,
                    "roleid": roleid
                }
            else:
                return {
                    "success": False,
                    "message": "Failed to assign role"
                }
        except Exception as e:
            return {
                "success": False,
                "message": f"Error assigning role: {str(e)}"
            }
    
    def check_host_interface_availability(
        self,
        hostid: str
    ) -> Dict[str, Any]:
        """
        Check if host interface is available (agent connected).
        
        Args:
            hostid: Host ID
        
        Returns:
            Dict with:
                - hostid: str
                - status: str ("available", "checking", "unavailable", "unknown")
                - available: int (0=unknown, 1=available, 2=checking, 3=unavailable)
                - interfaces: list of interface details
        """
        try:
            # Get host and interface info
            hosts = self.client.api_call("host.get", {
                "output": ["hostid", "host", "status"],
                "selectInterfaces": ["interfaceid", "ip", "port", "available"],
                "hostids": hostid
            })
            
            if not hosts:
                return {
                    "hostid": hostid,
                    "status": "unknown",
                    "available": 0,
                    "interfaces": [],
                    "error": "Host not found"
                }
            
            host = hosts[0]
            interfaces = host.get("interfaces", [])
            
            # Determine overall availability from interfaces
            availability_map = {
                "0": "unknown",
                "1": "available",
                "2": "checking",
                "3": "unavailable"
            }
            
            # Get most recent/primary interface status
            primary_status = "unknown"
            primary_available = 0
            
            if interfaces:
                primary = interfaces[0]
                primary_available = int(primary.get("available", 0))
                primary_status = availability_map.get(str(primary_available), "unknown")
            
            return {
                "hostid": hostid,
                "host": host.get("host"),
                "status": primary_status,
                "available": primary_available,
                "interfaces": interfaces
            }
        
        except Exception as e:
            return {
                "hostid": hostid,
                "status": "unknown",
                "available": 0,
                "interfaces": [],
                "error": str(e)
            }
    
    def _resolve_role_id(self, role: str) -> Optional[str]:
        """
        Resolve role name to ID.
        
        Args:
            role: Role ID or name
        
        Returns:
            Role ID or None if not found
        """
        # If already looks like an ID, return it
        if role.isdigit():
            return role
        
        # Search by name
        try:
            roles = self.client.api_call("role.get", {
                "output": ["roleid", "name"],
                "filter": {"name": role}
            })
            
            if roles:
                return roles[0]["roleid"]
        except Exception:
            pass
        
        return None
    
    def _get_user_groups_by_email(self, email: str) -> List[Dict[str, str]]:
        """
        Get user groups (not implemented yet, placeholder).
        
        Args:
            email: Email address
        
        Returns:
            List of user groups
        """
        # This could be enhanced to look up user groups by email domain
        # For now, returns empty list
        return []
