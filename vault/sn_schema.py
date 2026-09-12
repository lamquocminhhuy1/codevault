"""Per-component ServiceNow table schema, used to render/store the extra
metadata fields each script type actually has on the platform (e.g. a
Business Rule's ``active``/``abort_action``, a Scheduled Job's run
schedule, a UI Action's button-placement flags).

This mirrors the real sys_script / sys_script_client / sys_script_include /
sys_ui_action / sysauto_script / sys_script_fix / sys_ws_operation /
sp_widget / sys_ui_page / sys_ui_macro tables closely enough to be useful
as a reference, but field lists can vary slightly by ServiceNow version -
treat this as "close enough to store the details that matter", not a
byte-exact dictionary export.

Each entry: {"key", "label", "type", "help" (optional), "default"
(optional), "choices" (required when type == "select")}. ``type`` is one
of "text", "textarea", "boolean", "integer", "select". Values are stored
in Item.extra_fields, keyed by "key", scoped to the item's script_type.
"""

SCRIPT_TYPE_SCHEMAS = {
    "business_rule": [
        {"key": "active", "label": "Active", "type": "boolean", "default": True},
        {
            "key": "advanced",
            "label": "Advanced",
            "type": "boolean",
            "help": "Uses a script condition instead of the simple filter builder.",
        },
        {"key": "add_message", "label": "Add message", "type": "boolean"},
        {
            "key": "message",
            "label": "Message",
            "type": "textarea",
            "help": "Shown to the user when Add message is on.",
        },
        {
            "key": "abort_action",
            "label": "Abort action",
            "type": "boolean",
            "help": "Prevents the insert/update when the condition is true.",
        },
        {
            "key": "priority",
            "label": "Priority",
            "type": "integer",
            "help": "Execution order among rules with the same When/table (lower runs first).",
        },
    ],
    "client_script": [
        {
            "key": "ui_type",
            "label": "UI type",
            "type": "select",
            "choices": [("0", "All"), ("1", "Desktop"), ("10", "Mobile / Service Portal")],
        },
        {"key": "isolate_script", "label": "Isolate script", "type": "boolean", "default": True},
        {
            "key": "applies_extended",
            "label": "Inherited",
            "type": "boolean",
            "help": "Also runs on tables that extend this table.",
        },
        {
            "key": "messages",
            "label": "Messages",
            "type": "text",
            "help": "Comma-separated i18n message keys fetched via getMessage().",
        },
    ],
    "script_include": [
        {
            "key": "access",
            "label": "Accessible from",
            "type": "select",
            "choices": [
                ("package_private", "This application scope only"),
                ("public", "All application scopes"),
                ("protected", "All application scopes, but requires explicit access"),
            ],
        },
        {"key": "active", "label": "Active", "type": "boolean", "default": True},
    ],
    "ui_action": [
        {
            "key": "action_name",
            "label": "Action name",
            "type": "text",
            "help": "Internal sys_name used by scripts/URLs to reference this action.",
        },
        {"key": "order", "label": "Order", "type": "integer"},
        {"key": "active", "label": "Active", "type": "boolean", "default": True},
        {
            "key": "client",
            "label": "Client",
            "type": "boolean",
            "help": "Runs onclick in the browser instead of the server script.",
        },
        {
            "key": "onclick",
            "label": "onclick",
            "type": "text",
            "help": "Client-side function called when Client is on.",
        },
        {"key": "form_button", "label": "Form button", "type": "boolean"},
        {"key": "form_link", "label": "Form link (not a button)", "type": "boolean"},
        {"key": "list_action", "label": "List button", "type": "boolean"},
        {"key": "list_banner_button", "label": "List banner button", "type": "boolean"},
        {"key": "list_context_menu", "label": "List context menu", "type": "boolean"},
        {"key": "show_insert", "label": "Shows on new record (insert)", "type": "boolean", "default": True},
        {"key": "show_update", "label": "Shows on existing record (update)", "type": "boolean", "default": True},
        {"key": "hint", "label": "Hint", "type": "text"},
    ],
    "scheduled_job": [
        {
            "key": "run_type",
            "label": "Run",
            "type": "select",
            "choices": [
                ("periodically", "Periodically"),
                ("daily", "Daily"),
                ("weekly", "Weekly"),
                ("monthly", "Monthly"),
                ("once", "Once"),
                ("on_demand", "On demand"),
            ],
        },
        {"key": "run_time", "label": "Time", "type": "text", "help": "e.g. 02:00:00"},
        {"key": "run_dayofweek", "label": "Day of week", "type": "text", "help": "Weekly runs only."},
        {
            "key": "run_period",
            "label": "Repeat interval",
            "type": "text",
            "help": "e.g. every 30 minutes (Periodically only).",
        },
        {"key": "active", "label": "Active", "type": "boolean", "default": True},
        {
            "key": "conditional",
            "label": "Conditional",
            "type": "boolean",
            "help": "Only runs when the condition script returns true.",
        },
    ],
    "fix_script": [
        {"key": "run_manually", "label": "Run manually only", "type": "boolean", "default": True},
        {"key": "active", "label": "Active", "type": "boolean", "default": True},
    ],
    "rest_api": [
        {
            "key": "http_method",
            "label": "HTTP method",
            "type": "select",
            "choices": [("GET", "GET"), ("POST", "POST"), ("PUT", "PUT"), ("PATCH", "PATCH"), ("DELETE", "DELETE")],
        },
        {"key": "relative_path", "label": "Relative path", "type": "text", "help": "e.g. /things/{id}"},
        {"key": "requires_authentication", "label": "Requires authentication", "type": "boolean", "default": True},
        {"key": "requires_acl_authorization", "label": "Requires ACL authorization", "type": "boolean", "default": True},
        {"key": "active", "label": "Active", "type": "boolean", "default": True},
    ],
    "widget": [
        {"key": "public", "label": "Public (no login required)", "type": "boolean"},
        {"key": "has_preview", "label": "Has preview", "type": "boolean"},
        {
            "key": "option_schema",
            "label": "Option schema (JSON)",
            "type": "textarea",
            "help": 'Widget options exposed to the instance, e.g. [{"name":"title","type":"string"}]',
        },
    ],
    "ui_page": [
        {
            "key": "category",
            "label": "Category",
            "type": "select",
            "choices": [("general", "General"), ("homepage", "Homepage")],
        },
        {
            "key": "direct",
            "label": "Direct (no chrome)",
            "type": "boolean",
            "help": "Renders without the standard UI header/footer.",
        },
    ],
    "ui_macro": [
        {"key": "active", "label": "Active", "type": "boolean", "default": True},
    ],
}
