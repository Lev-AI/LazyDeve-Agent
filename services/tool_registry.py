"""
Tool Registry for MCP Preparation
Centralizes tool definitions for future MCP integration
"""

from typing import Dict, Callable, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime


@dataclass
class Tool:
    """
    Tool definition for MCP compatibility.
    """
    name: str
    description: str
    handler: Callable
    parameters: Dict[str, Any]
    category: str
    version: str = "1.0.0"
    registered_at: Optional[datetime] = None


class ToolRegistry:
    """
    Centralized registry for tools/endpoints.
    Prepares architecture for MCP (Model Context Protocol) migration.
    
    Future: This will be the bridge between LazyDeve and MCP servers.
    """
    
    def __init__(self):
        self._tools: Dict[str, Tool] = {}
        self._categories: Dict[str, List[str]] = {}
    
    def register(
        self,
        name: str,
        description: str,
        handler: Callable,
        parameters: Dict[str, Any],
        category: str = "general"
    ) -> None:
        """
        Register a tool/endpoint.
        
        Args:
            name: Unique tool identifier
            description: What the tool does
            handler: Function to execute
            parameters: Parameter schema
            category: Tool category (memory, docs, git, etc.)
        """
        tool = Tool(
            name=name,
            description=description,
            handler=handler,
            parameters=parameters,
            category=category,
            registered_at=datetime.now()
        )
        
        self._tools[name] = tool
        
        if category not in self._categories:
            self._categories[category] = []
        self._categories[category].append(name)
    
    def get_tool(self, name: str) -> Optional[Tool]:
        """Get tool by name."""
        return self._tools.get(name)
    
    def get_tools_by_category(self, category: str) -> List[Tool]:
        """Get all tools in a category."""
        tool_names = self._categories.get(category, [])
        return [self._tools[name] for name in tool_names if name in self._tools]
    
    def list_tools(self) -> List[str]:
        """List all registered tool names."""
        return list(self._tools.keys())
    
    def list_categories(self) -> List[str]:
        """List all tool categories."""
        return list(self._categories.keys())
    
    def get_tool_schema(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Get MCP-compatible schema for a tool.
        
        Returns:
            Schema dict or None if tool not found
        """
        tool = self.get_tool(name)
        if not tool:
            return None
        
        return {
            "name": tool.name,
            "description": tool.description,
            "parameters": tool.parameters,
            "category": tool.category,
            "version": tool.version
        }
    
    def unregister(self, name: str) -> bool:
        """
        Unregister a tool.
        
        Returns:
            True if tool was removed, False if not found
        """
        tool = self._tools.pop(name, None)
        if tool:
            # Remove from category list
            if tool.category in self._categories:
                self._categories[tool.category] = [
                    n for n in self._categories[tool.category] if n != name
                ]
            return True
        return False


# Singleton instance
_registry: Optional[ToolRegistry] = None


def get_tool_registry() -> ToolRegistry:
    """
    Get singleton ToolRegistry instance.
    
    Returns:
        ToolRegistry singleton
    """
    global _registry
    if _registry is None:
        _registry = ToolRegistry()
    return _registry

