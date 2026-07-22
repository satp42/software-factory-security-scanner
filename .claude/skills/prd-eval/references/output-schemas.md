# Output Schemas (verbatim)

The three output JSON schemas below are emitted verbatim from `api-gateway/src/lib/schemas.ts`. Match them exactly when producing evaluation output — the hosted validator uses `additionalProperties: false` and will reject any extra or missing required fields.

**Do not edit by hand.** Regenerate from the service with:

```bash
# inside api-gateway/
npm run build
node --input-type=module -e "import {BinaryScoreOutput, FixPlanOutput, AgentTasksOutput, BinaryScoreInput, FixPlanInput, AgentTasksInput} from './dist/lib/schemas.js'; console.log(JSON.stringify({BinaryScoreInput, BinaryScoreOutput, FixPlanInput, FixPlanOutput, AgentTasksInput, AgentTasksOutput}, null, 2));"
```

## Input schemas

Each endpoint accepts a body matching one of these input schemas. Defaults mirror the production service.

### BinaryScoreInput

```json
{
  "type": "object",
  "allOf": [
    {
      "type": "object",
      "required": [
        "prd_text"
      ],
      "properties": {
        "prd_text": {
          "type": "string"
        },
        "artifacts": {
          "type": "array",
          "items": {
            "type": "object",
            "required": [
              "name",
              "content",
              "kind"
            ],
            "properties": {
              "name": {
                "type": "string"
              },
              "content": {
                "type": "string"
              },
              "kind": {
                "type": "string",
                "enum": [
                  "note",
                  "email",
                  "call_notes",
                  "jira",
                  "spec",
                  "other"
                ]
              }
            },
            "additionalProperties": false
          }
        },
        "sections": {
          "type": "array",
          "items": {
            "type": "string"
          }
        },
        "rubric_version": {
          "type": "string",
          "default": "v1.0"
        }
      },
      "additionalProperties": false
    }
  ],
  "properties": {
    "prd_text": {
      "type": "string"
    },
    "artifacts": {
      "type": "array",
      "items": {
        "type": "object",
        "required": [
          "name",
          "content",
          "kind"
        ],
        "properties": {
          "name": {
            "type": "string"
          },
          "content": {
            "type": "string"
          },
          "kind": {
            "type": "string",
            "enum": [
              "note",
              "email",
              "call_notes",
              "jira",
              "spec",
              "other"
            ]
          }
        },
        "additionalProperties": false
      }
    },
    "sections": {
      "type": "array",
      "items": {
        "type": "string"
      }
    },
    "rubric_version": {
      "type": "string",
      "default": "v1.0"
    },
    "evidence_per_criterion": {
      "type": "integer",
      "default": 1,
      "minimum": 0,
      "maximum": 3
    },
    "fail_on_missing": {
      "type": "boolean",
      "default": true
    },
    "peer_reviews": {
      "type": "array",
      "items": {
        "type": "object",
        "required": [
          "criteria"
        ],
        "properties": {
          "criteria": {
            "type": "array",
            "items": {
              "type": "object",
              "required": [
                "id",
                "pass"
              ],
              "properties": {
                "id": {
                  "type": "string",
                  "pattern": "^C(1|2|3|4|5|6|7|8|9|10|11|12)$"
                },
                "pass": {
                  "type": "boolean"
                }
              },
              "additionalProperties": false
            }
          }
        },
        "additionalProperties": false
      }
    }
  },
  "additionalProperties": false
}
```

### FixPlanInput

```json
{
  "type": "object",
  "allOf": [
    {
      "type": "object",
      "required": [
        "prd_text"
      ],
      "properties": {
        "prd_text": {
          "type": "string"
        },
        "artifacts": {
          "type": "array",
          "items": {
            "type": "object",
            "required": [
              "name",
              "content",
              "kind"
            ],
            "properties": {
              "name": {
                "type": "string"
              },
              "content": {
                "type": "string"
              },
              "kind": {
                "type": "string",
                "enum": [
                  "note",
                  "email",
                  "call_notes",
                  "jira",
                  "spec",
                  "other"
                ]
              }
            },
            "additionalProperties": false
          }
        },
        "sections": {
          "type": "array",
          "items": {
            "type": "string"
          }
        },
        "rubric_version": {
          "type": "string",
          "default": "v1.0"
        }
      },
      "additionalProperties": false
    }
  ],
  "properties": {
    "prd_text": {
      "type": "string"
    },
    "artifacts": {
      "type": "array",
      "items": {
        "type": "object",
        "required": [
          "name",
          "content",
          "kind"
        ],
        "properties": {
          "name": {
            "type": "string"
          },
          "content": {
            "type": "string"
          },
          "kind": {
            "type": "string",
            "enum": [
              "note",
              "email",
              "call_notes",
              "jira",
              "spec",
              "other"
            ]
          }
        },
        "additionalProperties": false
      }
    },
    "sections": {
      "type": "array",
      "items": {
        "type": "string"
      }
    },
    "rubric_version": {
      "type": "string",
      "default": "v1.0"
    },
    "limit": {
      "type": "integer",
      "default": 10,
      "minimum": 1
    },
    "time_horizon_days": {
      "type": "integer",
      "default": 10
    },
    "include_acceptance_tests": {
      "type": "boolean",
      "default": true
    }
  },
  "additionalProperties": false
}
```

### AgentTasksInput

```json
{
  "type": "object",
  "allOf": [
    {
      "type": "object",
      "required": [
        "prd_text"
      ],
      "properties": {
        "prd_text": {
          "type": "string"
        },
        "artifacts": {
          "type": "array",
          "items": {
            "type": "object",
            "required": [
              "name",
              "content",
              "kind"
            ],
            "properties": {
              "name": {
                "type": "string"
              },
              "content": {
                "type": "string"
              },
              "kind": {
                "type": "string",
                "enum": [
                  "note",
                  "email",
                  "call_notes",
                  "jira",
                  "spec",
                  "other"
                ]
              }
            },
            "additionalProperties": false
          }
        },
        "sections": {
          "type": "array",
          "items": {
            "type": "string"
          }
        },
        "rubric_version": {
          "type": "string",
          "default": "v1.0"
        }
      },
      "additionalProperties": false
    }
  ],
  "properties": {
    "prd_text": {
      "type": "string"
    },
    "artifacts": {
      "type": "array",
      "items": {
        "type": "object",
        "required": [
          "name",
          "content",
          "kind"
        ],
        "properties": {
          "name": {
            "type": "string"
          },
          "content": {
            "type": "string"
          },
          "kind": {
            "type": "string",
            "enum": [
              "note",
              "email",
              "call_notes",
              "jira",
              "spec",
              "other"
            ]
          }
        },
        "additionalProperties": false
      }
    },
    "sections": {
      "type": "array",
      "items": {
        "type": "string"
      }
    },
    "rubric_version": {
      "type": "string",
      "default": "v1.0"
    },
    "task_hours_min": {
      "type": "number",
      "default": 2
    },
    "task_hours_max": {
      "type": "number",
      "default": 4
    },
    "feature_filter": {
      "type": "array",
      "items": {
        "type": "string"
      }
    },
    "emit_mermaid": {
      "type": "boolean",
      "default": false
    }
  },
  "additionalProperties": false
}
```

## Output schemas

### BinaryScoreOutput

```json
{
  "type": "object",
  "required": [
    "rubric_version",
    "prd_title",
    "pass_count",
    "fail_count",
    "criteria",
    "gating_failures",
    "readiness_gate",
    "compliance",
    "agreement"
  ],
  "properties": {
    "rubric_version": {
      "type": "string"
    },
    "prd_title": {
      "type": "string"
    },
    "pass_count": {
      "type": "integer"
    },
    "fail_count": {
      "type": "integer"
    },
    "criteria": {
      "type": "array",
      "items": {
        "type": "object",
        "required": [
          "id",
          "name",
          "pass",
          "status",
          "rationale",
          "evidence"
        ],
        "properties": {
          "id": {
            "type": "string",
            "pattern": "^C(1|2|3|4|5|6|7|8|9|10|11|12)$"
          },
          "name": {
            "type": "string"
          },
          "pass": {
            "type": "boolean"
          },
          "status": {
            "type": "string",
            "enum": [
              "pass",
              "fail"
            ]
          },
          "rationale": {
            "type": "string"
          },
          "evidence": {
            "type": "array",
            "items": {
              "type": "object",
              "required": [
                "quote",
                "locator"
              ],
              "properties": {
                "quote": {
                  "type": "string"
                },
                "locator": {
                  "type": "object",
                  "required": [
                    "section",
                    "page"
                  ],
                  "properties": {
                    "section": {
                      "type": "string"
                    },
                    "page": {
                      "type": "string"
                    }
                  },
                  "additionalProperties": false
                }
              },
              "additionalProperties": false
            }
          }
        },
        "additionalProperties": false
      }
    },
    "compliance": {
      "type": "object",
      "required": [
        "gaps_count",
        "gaps"
      ],
      "properties": {
        "gaps_count": {
          "type": "integer"
        },
        "gaps": {
          "type": "array",
          "items": {
            "type": "object",
            "required": [
              "area",
              "note",
              "linked_criteria"
            ],
            "properties": {
              "area": {
                "type": "string",
                "enum": [
                  "AuditTrail",
                  "RBAC",
                  "ALCOA+",
                  "Part11",
                  "Validation",
                  "PHI/HIPAA",
                  "Veeva/Vault",
                  "LIMS/EMR",
                  "Other"
                ]
              },
              "note": {
                "type": "string"
              },
              "linked_criteria": {
                "type": "array",
                "items": {
                  "type": "string",
                  "pattern": "^C(5|10)$"
                }
              }
            },
            "additionalProperties": false
          }
        }
      },
      "additionalProperties": false
    },
    "gating_failures": {
      "type": "array",
      "items": {
        "type": "string"
      }
    },
    "readiness_gate": {
      "type": "object",
      "required": [
        "state",
        "must_pass_met",
        "total_pass",
        "reason"
      ],
      "properties": {
        "state": {
          "type": "string",
          "enum": [
            "GO",
            "REVISE",
            "HOLD"
          ]
        },
        "must_pass_met": {
          "type": "boolean"
        },
        "total_pass": {
          "type": "integer"
        },
        "reason": {
          "type": "string"
        }
      },
      "additionalProperties": false
    },
    "agreement": {
      "type": "object",
      "required": [
        "present",
        "percent_agreement",
        "by_criterion"
      ],
      "properties": {
        "present": {
          "type": "boolean"
        },
        "percent_agreement": {
          "type": "number"
        },
        "by_criterion": {
          "type": "array",
          "items": {
            "type": "object",
            "required": [
              "id",
              "agreement_pct"
            ],
            "properties": {
              "id": {
                "type": "string",
                "pattern": "^C(1|2|3|4|5|6|7|8|9|10|11|12)$"
              },
              "agreement_pct": {
                "type": "number"
              }
            },
            "additionalProperties": false
          }
        }
      },
      "additionalProperties": false
    }
  },
  "additionalProperties": false
}
```

### FixPlanOutput

```json
{
  "type": "object",
  "required": [
    "items"
  ],
  "properties": {
    "items": {
      "type": "array",
      "items": {
        "type": "object",
        "required": [
          "id",
          "title",
          "priority",
          "owner",
          "blocking",
          "effort",
          "impact",
          "description",
          "steps",
          "acceptance_tests",
          "linked_criteria"
        ],
        "properties": {
          "id": {
            "type": "string"
          },
          "title": {
            "type": "string"
          },
          "priority": {
            "type": "string",
            "pattern": "^P[0-2]$"
          },
          "owner": {
            "type": "string"
          },
          "blocking": {
            "type": "boolean"
          },
          "effort": {
            "type": "string",
            "enum": [
              "S",
              "M",
              "L"
            ]
          },
          "impact": {
            "type": "string",
            "enum": [
              "Low",
              "Med",
              "High"
            ]
          },
          "description": {
            "type": "string"
          },
          "steps": {
            "type": "array",
            "items": {
              "type": "string"
            }
          },
          "acceptance_tests": {
            "type": "array",
            "items": {
              "type": "string"
            }
          },
          "linked_criteria": {
            "type": "array",
            "items": {
              "type": "string",
              "pattern": "^C(1|2|3|4|5|6|7|8|9|10|11|12)$"
            }
          }
        },
        "additionalProperties": false
      }
    }
  },
  "additionalProperties": false
}
```

### AgentTasksOutput

```json
{
  "type": "object",
  "required": [
    "tasks",
    "edges"
  ],
  "properties": {
    "tasks": {
      "type": "array",
      "items": {
        "type": "object",
        "required": [
          "id",
          "feature",
          "title",
          "description",
          "duration",
          "est_hours",
          "owner_role",
          "entry",
          "exit",
          "test",
          "entry_conditions",
          "exit_conditions",
          "tests",
          "inputs",
          "outputs",
          "status"
        ],
        "properties": {
          "id": {
            "type": "string"
          },
          "feature": {
            "type": "string"
          },
          "title": {
            "type": "string"
          },
          "description": {
            "type": "string"
          },
          "duration": {
            "type": "string",
            "pattern": "^[0-9]+(h|hr|hours?)$"
          },
          "est_hours": {
            "type": "number"
          },
          "owner_role": {
            "type": "string"
          },
          "entry": {
            "type": "string"
          },
          "exit": {
            "type": "string"
          },
          "test": {
            "type": "string"
          },
          "entry_conditions": {
            "type": "array",
            "items": {
              "type": "string"
            }
          },
          "exit_conditions": {
            "type": "array",
            "items": {
              "type": "string"
            }
          },
          "tests": {
            "type": "array",
            "items": {
              "type": "string"
            }
          },
          "inputs": {
            "type": "array",
            "items": {
              "type": "string"
            }
          },
          "outputs": {
            "type": "array",
            "items": {
              "type": "string"
            }
          },
          "status": {
            "type": "string",
            "enum": [
              "ready",
              "blocked",
              "in_progress",
              "completed"
            ]
          }
        },
        "additionalProperties": false
      }
    },
    "edges": {
      "type": "array",
      "items": {
        "type": "object",
        "required": [
          "from",
          "to",
          "type"
        ],
        "properties": {
          "from": {
            "type": "string"
          },
          "to": {
            "type": "string"
          },
          "type": {
            "type": "string",
            "enum": [
              "depends_on",
              "blocks",
              "related"
            ]
          }
        },
        "additionalProperties": false
      }
    },
    "mermaid": {
      "type": "string"
    }
  },
  "additionalProperties": false
}
```

## Critical conformance notes

- **BinaryScoreOutput.criteria**: `required` includes `id, name, pass, status, rationale, evidence`. Must contain all 12 entries C1–C12. `status` is lowercase `"pass"`/`"fail"`; `pass` boolean must agree.
- **BinaryScoreOutput.readiness_gate.state**: UPPERCASE enum `"GO" | "REVISE" | "HOLD"`.
- **BinaryScoreOutput.compliance.gaps[].area**: enum `AuditTrail | RBAC | ALCOA+ | Part11 | Validation | PHI/HIPAA | Veeva/Vault | LIMS/EMR | Other`. `linked_criteria[]` restricted to `C5` or `C10`.
- **BinaryScoreOutput.agreement**: required even when `present: false` — provide `{present: false, percent_agreement: 0, by_criterion: []}`.
- **FixPlanOutput.items[]**: every field in `required` must be present, including `acceptance_tests` (empty array allowed if `include_acceptance_tests: false` was requested). `priority` regex `^P[0-2]$`. `effort` enum `S | M | L`. `impact` enum `Low | Med | High`.
- **AgentTasksOutput.tasks[]**: `required` lists **all** of `id, feature, title, description, duration, est_hours, owner_role, entry, exit, test, entry_conditions, exit_conditions, tests, inputs, outputs, status`. The Mode 3 prompt says these arrays are "optional" — the schema disagrees. Always emit them as populated arrays (use one-element arrays mirroring the singular `entry`/`exit`/`test` strings if no richer data is available).
- **AgentTasksOutput.tasks[].duration**: regex `^[0-9]+(h|hr|hours?)$`. Strings like `"2h"`, `"4h"`, `"3hours"` all match; `"2"` alone does not.
- **AgentTasksOutput.tasks[].status**: enum `ready | blocked | in_progress | completed`.
- **AgentTasksOutput.edges[]**: `type` enum `depends_on | blocks | related`. Every `from`/`to` must reference an existing task `id`. `mermaid` is optional — omit unless `emit_mermaid: true` was requested.

## Self-check before returning JSON

Before emitting any of the three outputs, walk the schema's `required` array field-by-field and confirm every property is present with the correct type. If a required field is missing because the PRD lacks the source material, emit a placeholder string and note the absence in the rationale rather than omitting the field.
