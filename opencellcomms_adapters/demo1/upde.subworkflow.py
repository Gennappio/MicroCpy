{
  "format": "subworkflow",
  "version": "1.0",
  "name": "upde",
  "kind": "agent_behavior",
  "description": "cellulina behavior: upde",
  "exported_from": "Untitled Workflow",
  "exported_at": "2026-06-08T13:52:45.884Z",
  "subworkflow": {
    "description": "cellulina behavior: upde",
    "enabled": true,
    "deletable": true,
    "controller": {
      "id": "controller-upde",
      "label": "UPDE CONTROLLER",
      "position": {
        "x": 100,
        "y": 100
      },
      "number_of_steps": 1
    },
    "functions": [
      {
        "id": "func1_1780926753649",
        "function_name": "func1",
        "parameters": {},
        "enabled": true,
        "verbose": false,
        "position": {
          "x": 148.47949360196324,
          "y": 239.68554467216808
        },
        "description": "✱ unsaved — click Export Behavior to write the file",
        "custom_name": "",
        "parameter_nodes": [],
        "step_count": 1
      }
    ],
    "subworkflow_calls": [],
    "parameters": [],
    "execution_order": [
      "func1_1780926753649"
    ],
    "input_parameters": []
  },
  "dependencies": {
    "subworkflows_referenced": [],
    "functions_required": [
      "func1"
    ]
  }
}