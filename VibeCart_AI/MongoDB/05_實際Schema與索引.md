# Atlas 最新完整 Schema 讀回

新版核心 19 集合 v4，另保留 8 集合。

```json
{
  "checked_at": {
    "$date": "2026-09-18T16:07:10.833Z"
  },
  "database": "vibecart_ai",
  "core_collections": [
    "users",
    "products",
    "product_skus",
    "product_reviews",
    "product_repurchase_stats",
    "categories",
    "brands",
    "orders",
    "order_items",
    "carts",
    "cart_events",
    "behavior_events",
    "user_preference_scores",
    "cross_category_rules",
    "product_purchase_sequences",
    "recommendation_pools",
    "first_member_recommendations",
    "recommendation_logs",
    "system_configs"
  ],
  "preserved_collections": [
    "user_events",
    "ai_requests",
    "product_embeddings",
    "recommendations",
    "ai_insights",
    "ai_usage",
    "request_limits",
    "schema_migrations"
  ],
  "extra_collections": [],
  "migrations": [
    {
      "_id": "20260916_01_initial_schema_v2",
      "schema_version": 2,
      "checksum": "3478559fd54fbc72d3ba095eb22163600aa988a870cc31c1d29241206c59de5d",
      "status": "succeeded",
      "started_at": {
        "$date": "2026-09-16T02:52:38.287Z"
      },
      "completed_at": {
        "$date": "2026-09-16T02:52:42.945Z"
      },
      "counts": {
        "source": 0,
        "target": 0,
        "errors": 0
      },
      "error_code": null
    },
    {
      "_id": "20260916_02_cart_state_events_v3",
      "schema_version": 2,
      "checksum": "12728b76700f6d26ab29f6df9cdbcbf4bf1dad725608c4a7a7dc3455f71fcf4c",
      "status": "succeeded",
      "started_at": {
        "$date": "2026-09-16T14:02:43.918Z"
      },
      "completed_at": {
        "$date": "2026-09-16T14:02:50.391Z"
      },
      "counts": {
        "source": 0,
        "target": 0,
        "errors": 0
      },
      "error_code": null
    },
    {
      "_id": "20260918_03_schema_document_constraints",
      "schema_version": 2,
      "checksum": "29aa95e0c03db30c3c4891dbe6712ff21f7c7364de4ae40eb2eabccbcf862e05",
      "status": "succeeded",
      "started_at": {
        "$date": "2026-09-18T11:37:23.988Z"
      },
      "completed_at": {
        "$date": "2026-09-18T11:37:28.449Z"
      },
      "counts": {
        "source": 0,
        "target": 0,
        "errors": 0
      },
      "error_code": null
    },
    {
      "_id": "20260918_04_complete_catalog_schema_v4",
      "schema_version": 2,
      "checksum": "543eb3d495f9e5a3cef51ad38fda18a3d89b51a0659526b822ce4df37fd3e676",
      "status": "succeeded",
      "started_at": {
        "$date": "2026-09-18T15:58:10.194Z"
      },
      "completed_at": {
        "$date": "2026-09-18T15:58:25.664Z"
      },
      "counts": {
        "source": 0,
        "target": 1,
        "errors": 0
      },
      "error_code": null
    }
  ],
  "collections": [
    {
      "collection": "users",
      "count": 0,
      "conforming_documents": 0,
      "options": {
        "validator": {
          "$jsonSchema": {
            "bsonType": "object",
            "required": [
              "_id",
              "schema_version",
              "display_name",
              "email",
              "auth_provider",
              "password_hash",
              "firebase_uid",
              "role",
              "is_active",
              "preferences",
              "status",
              "member_level",
              "registered_at",
              "first_recommendation_generated_at",
              "last_login_at",
              "created_at",
              "updated_at"
            ],
            "properties": {
              "_id": {
                "bsonType": "objectId"
              },
              "schema_version": {
                "bsonType": "int",
                "enum": [
                  4
                ]
              },
              "display_name": {
                "bsonType": "string",
                "maxLength": 100,
                "minLength": 1
              },
              "email": {
                "bsonType": "string",
                "pattern": "^[^\\sA-Z]+$",
                "minLength": 1
              },
              "auth_provider": {
                "enum": [
                  "local"
                ]
              },
              "password_hash": {
                "bsonType": "string",
                "minLength": 1
              },
              "firebase_uid": {
                "bsonType": [
                  "string",
                  "null"
                ]
              },
              "role": {
                "enum": [
                  "customer",
                  "admin"
                ]
              },
              "is_active": {
                "bsonType": "bool"
              },
              "preferences": {
                "bsonType": "object",
                "required": [
                  "category_ids",
                  "tags",
                  "budget_min",
                  "budget_max",
                  "updated_at"
                ],
                "properties": {
                  "category_ids": {
                    "bsonType": "array",
                    "items": {
                      "bsonType": "objectId"
                    },
                    "minItems": 0,
                    "maxItems": 10,
                    "uniqueItems": true
                  },
                  "tags": {
                    "bsonType": "array",
                    "items": {
                      "bsonType": "string",
                      "maxLength": 30,
                      "minLength": 1
                    },
                    "minItems": 0,
                    "maxItems": 20,
                    "uniqueItems": true
                  },
                  "budget_min": {
                    "bsonType": [
                      "decimal",
                      "null"
                    ],
                    "minimum": {
                      "$numberDecimal": "0"
                    }
                  },
                  "budget_max": {
                    "bsonType": [
                      "decimal",
                      "null"
                    ],
                    "minimum": {
                      "$numberDecimal": "0"
                    }
                  },
                  "updated_at": {
                    "bsonType": [
                      "date",
                      "null"
                    ]
                  }
                },
                "additionalProperties": false
              },
              "status": {
                "enum": [
                  "active",
                  "inactive"
                ]
              },
              "member_level": {
                "bsonType": "string",
                "maxLength": 50,
                "minLength": 1
              },
              "registered_at": {
                "bsonType": "date"
              },
              "first_recommendation_generated_at": {
                "bsonType": [
                  "date",
                  "null"
                ]
              },
              "last_login_at": {
                "bsonType": [
                  "date",
                  "null"
                ]
              },
              "created_at": {
                "bsonType": "date"
              },
              "updated_at": {
                "bsonType": "date"
              }
            },
            "additionalProperties": false
          },
          "$and": [
            {
              "$expr": {
                "$or": [
                  {
                    "$eq": [
                      "$preferences.budget_min",
                      null
                    ]
                  },
                  {
                    "$eq": [
                      "$preferences.budget_max",
                      null
                    ]
                  },
                  {
                    "$lte": [
                      "$preferences.budget_min",
                      "$preferences.budget_max"
                    ]
                  }
                ]
              }
            },
            {
              "$expr": {
                "$or": [
                  {
                    "$eq": [
                      "$preferences.budget_min",
                      null
                    ]
                  },
                  {
                    "$and": [
                      {
                        "$lte": [
                          "$preferences.budget_min",
                          {
                            "$numberDecimal": "1.000000000000000000000000000000000E+6144"
                          }
                        ]
                      },
                      {
                        "$eq": [
                          "$preferences.budget_min",
                          {
                            "$round": [
                              "$preferences.budget_min",
                              2
                            ]
                          }
                        ]
                      }
                    ]
                  }
                ]
              }
            },
            {
              "$expr": {
                "$or": [
                  {
                    "$eq": [
                      "$preferences.budget_max",
                      null
                    ]
                  },
                  {
                    "$and": [
                      {
                        "$lte": [
                          "$preferences.budget_max",
                          {
                            "$numberDecimal": "1.000000000000000000000000000000000E+6144"
                          }
                        ]
                      },
                      {
                        "$eq": [
                          "$preferences.budget_max",
                          {
                            "$round": [
                              "$preferences.budget_max",
                              2
                            ]
                          }
                        ]
                      }
                    ]
                  }
                ]
              }
            },
            {
              "$expr": {
                "$eq": [
                  "$is_active",
                  {
                    "$eq": [
                      "$status",
                      "active"
                    ]
                  }
                ]
              }
            }
          ]
        },
        "validationLevel": "strict",
        "validationAction": "error"
      },
      "indexes": [
        {
          "v": 2,
          "key": {
            "_id": 1
          },
          "name": "_id_"
        },
        {
          "v": 2,
          "key": {
            "email": 1
          },
          "name": "uq_users_email",
          "unique": true
        },
        {
          "v": 2,
          "key": {
            "firebase_uid": 1
          },
          "name": "uq_users_firebase_uid",
          "unique": true,
          "partialFilterExpression": {
            "firebase_uid": {
              "$type": "string"
            }
          }
        },
        {
          "v": 2,
          "key": {
            "registered_at": 1
          },
          "name": "idx_users_registered_at"
        }
      ]
    },
    {
      "collection": "categories",
      "count": 0,
      "conforming_documents": 0,
      "options": {
        "validator": {
          "$jsonSchema": {
            "bsonType": "object",
            "required": [
              "_id",
              "schema_version",
              "category_code",
              "name",
              "level",
              "parent_id",
              "path",
              "status",
              "sort_order",
              "created_at",
              "updated_at"
            ],
            "properties": {
              "_id": {
                "bsonType": "objectId"
              },
              "schema_version": {
                "bsonType": "int",
                "enum": [
                  4
                ]
              },
              "category_code": {
                "bsonType": "string",
                "maxLength": 100,
                "minLength": 1
              },
              "name": {
                "bsonType": "string",
                "maxLength": 100,
                "minLength": 1
              },
              "level": {
                "bsonType": "int",
                "enum": [
                  1,
                  2
                ]
              },
              "parent_id": {
                "bsonType": [
                  "objectId",
                  "null"
                ]
              },
              "path": {
                "bsonType": "array",
                "items": {
                  "bsonType": "string",
                  "maxLength": 100,
                  "minLength": 1
                },
                "minItems": 1,
                "uniqueItems": false,
                "maxItems": 2
              },
              "status": {
                "enum": [
                  "active",
                  "inactive"
                ]
              },
              "sort_order": {
                "bsonType": "int",
                "minimum": 0
              },
              "created_at": {
                "bsonType": "date"
              },
              "updated_at": {
                "bsonType": "date"
              }
            },
            "additionalProperties": false
          },
          "$and": [
            {
              "$expr": {
                "$eq": [
                  {
                    "$size": "$path"
                  },
                  "$level"
                ]
              }
            },
            {
              "$expr": {
                "$eq": [
                  {
                    "$arrayElemAt": [
                      "$path",
                      -1
                    ]
                  },
                  "$category_code"
                ]
              }
            },
            {
              "$expr": {
                "$eq": [
                  {
                    "$eq": [
                      "$level",
                      1
                    ]
                  },
                  {
                    "$eq": [
                      "$parent_id",
                      null
                    ]
                  }
                ]
              }
            }
          ]
        },
        "validationLevel": "strict",
        "validationAction": "error"
      },
      "indexes": [
        {
          "v": 2,
          "key": {
            "_id": 1
          },
          "name": "_id_"
        },
        {
          "v": 2,
          "key": {
            "category_code": 1
          },
          "name": "uq_categories_category_code",
          "unique": true
        },
        {
          "v": 2,
          "key": {
            "parent_id": 1,
            "status": 1,
            "sort_order": 1
          },
          "name": "idx_categories_parent_id_status_sort_order"
        }
      ]
    },
    {
      "collection": "products",
      "count": 0,
      "conforming_documents": 0,
      "options": {
        "validator": {
          "$jsonSchema": {
            "bsonType": "object",
            "required": [
              "_id",
              "schema_version",
              "product_code",
              "product_name",
              "product_aliases",
              "brand_id",
              "major_category_id",
              "minor_category_id",
              "category_path",
              "summary",
              "description",
              "usage_scenarios",
              "target_segments",
              "product_tags",
              "status",
              "is_ai_recommendable",
              "image_urls",
              "shipping_profile_id",
              "rating_status",
              "rating_default_value",
              "rating_sum",
              "rating_count",
              "average_rating_raw",
              "average_rating_display",
              "rating_distribution",
              "product_lifecycle_type",
              "replenishment_enabled",
              "expected_repurchase_interval_days",
              "expected_purchase_frequency_year",
              "minimum_repeat_frequency_year",
              "replenishment_basis",
              "replenishment_confidence",
              "repeat_purchase_rate_12m",
              "repeat_customer_count_12m",
              "unique_buyer_count_12m",
              "order_count_12m",
              "avg_purchase_frequency_12m",
              "median_repurchase_interval_days",
              "last_repurchase_calculated_at",
              "created_at",
              "updated_at"
            ],
            "properties": {
              "_id": {
                "bsonType": "objectId"
              },
              "schema_version": {
                "bsonType": "int",
                "enum": [
                  4
                ]
              },
              "product_code": {
                "bsonType": "string",
                "maxLength": 100,
                "minLength": 1
              },
              "product_name": {
                "bsonType": "string",
                "maxLength": 200,
                "minLength": 1
              },
              "product_aliases": {
                "bsonType": "array",
                "items": {
                  "bsonType": "string",
                  "maxLength": 100,
                  "minLength": 1
                },
                "minItems": 0,
                "uniqueItems": true
              },
              "brand_id": {
                "bsonType": [
                  "objectId",
                  "null"
                ]
              },
              "major_category_id": {
                "bsonType": "objectId"
              },
              "minor_category_id": {
                "bsonType": "objectId"
              },
              "category_path": {
                "bsonType": "array",
                "items": {
                  "bsonType": "string",
                  "maxLength": 100,
                  "minLength": 1
                },
                "minItems": 2,
                "uniqueItems": false,
                "maxItems": 2
              },
              "summary": {
                "bsonType": "string",
                "maxLength": 1000,
                "minLength": 1
              },
              "description": {
                "bsonType": "string",
                "maxLength": 5000,
                "minLength": 1
              },
              "usage_scenarios": {
                "bsonType": "array",
                "items": {
                  "bsonType": "string",
                  "maxLength": 100,
                  "minLength": 1
                },
                "minItems": 0,
                "uniqueItems": true
              },
              "target_segments": {
                "bsonType": "array",
                "items": {
                  "bsonType": "string",
                  "maxLength": 100,
                  "minLength": 1
                },
                "minItems": 0,
                "uniqueItems": true
              },
              "product_tags": {
                "bsonType": "array",
                "items": {
                  "bsonType": "string",
                  "maxLength": 100,
                  "minLength": 1
                },
                "minItems": 0,
                "uniqueItems": true
              },
              "status": {
                "enum": [
                  "active",
                  "inactive",
                  "draft"
                ]
              },
              "is_ai_recommendable": {
                "bsonType": "bool"
              },
              "image_urls": {
                "bsonType": "array",
                "items": {
                  "bsonType": "string",
                  "pattern": "^(https://|/(?!/))"
                },
                "minItems": 0,
                "uniqueItems": false,
                "maxItems": 10
              },
              "shipping_profile_id": {
                "bsonType": [
                  "objectId",
                  "string",
                  "null"
                ]
              },
              "rating_status": {
                "enum": [
                  "DEFAULT",
                  "ACTUAL"
                ]
              },
              "rating_default_value": {
                "bsonType": [
                  "double",
                  "null"
                ],
                "minimum": 1,
                "maximum": 5
              },
              "rating_sum": {
                "bsonType": "int",
                "minimum": 0
              },
              "rating_count": {
                "bsonType": "int",
                "minimum": 0
              },
              "average_rating_raw": {
                "bsonType": [
                  "double",
                  "null"
                ],
                "minimum": 1,
                "maximum": 5
              },
              "average_rating_display": {
                "bsonType": "double",
                "minimum": 1,
                "maximum": 5
              },
              "rating_distribution": {
                "bsonType": "object",
                "required": [
                  "star_1",
                  "star_2",
                  "star_3",
                  "star_4",
                  "star_5"
                ],
                "properties": {
                  "star_1": {
                    "bsonType": "int",
                    "minimum": 0
                  },
                  "star_2": {
                    "bsonType": "int",
                    "minimum": 0
                  },
                  "star_3": {
                    "bsonType": "int",
                    "minimum": 0
                  },
                  "star_4": {
                    "bsonType": "int",
                    "minimum": 0
                  },
                  "star_5": {
                    "bsonType": "int",
                    "minimum": 0
                  }
                },
                "additionalProperties": false
              },
              "product_lifecycle_type": {
                "enum": [
                  "consumable",
                  "durable"
                ]
              },
              "replenishment_enabled": {
                "bsonType": "bool"
              },
              "expected_repurchase_interval_days": {
                "bsonType": [
                  "int",
                  "null"
                ],
                "minimum": 1
              },
              "expected_purchase_frequency_year": {
                "bsonType": [
                  "double",
                  "null"
                ],
                "minimum": 0,
                "maximum": 1.7976931348623157e+308
              },
              "minimum_repeat_frequency_year": {
                "bsonType": "double",
                "minimum": 0,
                "maximum": 1.7976931348623157e+308
              },
              "replenishment_basis": {
                "enum": [
                  "category_benchmark",
                  "historical"
                ]
              },
              "replenishment_confidence": {
                "bsonType": "double",
                "minimum": 0,
                "maximum": 1
              },
              "repeat_purchase_rate_12m": {
                "bsonType": [
                  "double",
                  "null"
                ],
                "minimum": 0,
                "maximum": 1
              },
              "repeat_customer_count_12m": {
                "bsonType": "int",
                "minimum": 0
              },
              "unique_buyer_count_12m": {
                "bsonType": "int",
                "minimum": 0
              },
              "order_count_12m": {
                "bsonType": "int",
                "minimum": 0
              },
              "avg_purchase_frequency_12m": {
                "bsonType": [
                  "double",
                  "null"
                ],
                "minimum": 0,
                "maximum": 1.7976931348623157e+308
              },
              "median_repurchase_interval_days": {
                "bsonType": [
                  "double",
                  "null"
                ],
                "minimum": 0,
                "maximum": 1.7976931348623157e+308
              },
              "last_repurchase_calculated_at": {
                "bsonType": [
                  "date",
                  "null"
                ]
              },
              "created_at": {
                "bsonType": "date"
              },
              "updated_at": {
                "bsonType": "date"
              }
            },
            "additionalProperties": false
          },
          "$and": [
            {
              "$expr": {
                "$eq": [
                  "$rating_count",
                  {
                    "$add": [
                      "$rating_distribution.star_1",
                      "$rating_distribution.star_2",
                      "$rating_distribution.star_3",
                      "$rating_distribution.star_4",
                      "$rating_distribution.star_5"
                    ]
                  }
                ]
              }
            },
            {
              "$expr": {
                "$eq": [
                  "$rating_sum",
                  {
                    "$add": [
                      {
                        "$multiply": [
                          1,
                          "$rating_distribution.star_1"
                        ]
                      },
                      {
                        "$multiply": [
                          2,
                          "$rating_distribution.star_2"
                        ]
                      },
                      {
                        "$multiply": [
                          3,
                          "$rating_distribution.star_3"
                        ]
                      },
                      {
                        "$multiply": [
                          4,
                          "$rating_distribution.star_4"
                        ]
                      },
                      {
                        "$multiply": [
                          5,
                          "$rating_distribution.star_5"
                        ]
                      }
                    ]
                  }
                ]
              }
            },
            {
              "$expr": {
                "$cond": [
                  {
                    "$eq": [
                      "$rating_count",
                      0
                    ]
                  },
                  {
                    "$and": [
                      {
                        "$eq": [
                          "$rating_status",
                          "DEFAULT"
                        ]
                      },
                      {
                        "$eq": [
                          "$rating_default_value",
                          4.0
                        ]
                      },
                      {
                        "$eq": [
                          "$average_rating_raw",
                          null
                        ]
                      },
                      {
                        "$eq": [
                          "$average_rating_display",
                          4.0
                        ]
                      }
                    ]
                  },
                  {
                    "$and": [
                      {
                        "$eq": [
                          "$rating_status",
                          "ACTUAL"
                        ]
                      },
                      {
                        "$in": [
                          "$rating_default_value",
                          [
                            null,
                            4.0
                          ]
                        ]
                      },
                      {
                        "$eq": [
                          "$average_rating_raw",
                          {
                            "$toDouble": {
                              "$divide": [
                                {
                                  "$toDecimal": "$rating_sum"
                                },
                                {
                                  "$toDecimal": "$rating_count"
                                }
                              ]
                            }
                          }
                        ]
                      },
                      {
                        "$eq": [
                          "$average_rating_display",
                          {
                            "$toDouble": {
                              "$divide": [
                                {
                                  "$ceil": {
                                    "$multiply": [
                                      {
                                        "$divide": [
                                          {
                                            "$toDecimal": "$rating_sum"
                                          },
                                          {
                                            "$toDecimal": "$rating_count"
                                          }
                                        ]
                                      },
                                      10
                                    ]
                                  }
                                },
                                10
                              ]
                            }
                          }
                        ]
                      }
                    ]
                  }
                ]
              }
            },
            {
              "$expr": {
                "$lte": [
                  "$repeat_customer_count_12m",
                  "$unique_buyer_count_12m"
                ]
              }
            }
          ]
        },
        "validationLevel": "strict",
        "validationAction": "error"
      },
      "indexes": [
        {
          "v": 2,
          "key": {
            "_id": 1
          },
          "name": "_id_"
        },
        {
          "v": 2,
          "key": {
            "product_code": 1
          },
          "name": "uq_products_product_code",
          "unique": true
        },
        {
          "v": 2,
          "key": {
            "major_category_id": 1,
            "minor_category_id": 1,
            "status": 1
          },
          "name": "idx_products_major_category_id_minor_category_id_status"
        },
        {
          "v": 2,
          "key": {
            "status": 1,
            "average_rating_display": -1
          },
          "name": "idx_products_status_average_rating_display"
        },
        {
          "v": 2,
          "key": {
            "is_ai_recommendable": 1,
            "status": 1,
            "major_category_id": 1
          },
          "name": "idx_products_is_ai_recommendable_status_major_category_id"
        }
      ]
    },
    {
      "collection": "carts",
      "count": 0,
      "conforming_documents": 0,
      "options": {
        "validator": {
          "$jsonSchema": {
            "bsonType": "object",
            "required": [
              "_id",
              "schema_version",
              "user_id",
              "status",
              "revision",
              "items",
              "created_at",
              "updated_at"
            ],
            "properties": {
              "_id": {
                "bsonType": "objectId"
              },
              "schema_version": {
                "bsonType": "int",
                "enum": [
                  4
                ]
              },
              "user_id": {
                "bsonType": "objectId"
              },
              "status": {
                "enum": [
                  "active",
                  "converted",
                  "abandoned"
                ]
              },
              "revision": {
                "bsonType": "int",
                "minimum": 0
              },
              "items": {
                "bsonType": "array",
                "items": {
                  "bsonType": "object",
                  "required": [
                    "product_id",
                    "quantity",
                    "price_snapshot",
                    "added_at",
                    "updated_at",
                    "sku_id"
                  ],
                  "properties": {
                    "product_id": {
                      "bsonType": "objectId"
                    },
                    "quantity": {
                      "bsonType": "int",
                      "minimum": 1,
                      "maximum": 99
                    },
                    "price_snapshot": {
                      "bsonType": "decimal",
                      "minimum": {
                        "$numberDecimal": "0"
                      }
                    },
                    "added_at": {
                      "bsonType": "date"
                    },
                    "updated_at": {
                      "bsonType": "date"
                    },
                    "sku_id": {
                      "bsonType": "objectId"
                    }
                  },
                  "additionalProperties": false
                },
                "minItems": 0,
                "maxItems": 20,
                "uniqueItems": false
              },
              "created_at": {
                "bsonType": "date"
              },
              "updated_at": {
                "bsonType": "date"
              }
            },
            "additionalProperties": false
          },
          "$and": [
            {
              "$expr": {
                "$eq": [
                  {
                    "$size": "$items"
                  },
                  {
                    "$size": {
                      "$setUnion": [
                        "$items.sku_id",
                        []
                      ]
                    }
                  }
                ]
              }
            },
            {
              "$expr": {
                "$allElementsTrue": [
                  {
                    "$map": {
                      "input": "$items",
                      "as": "i",
                      "in": {
                        "$and": [
                          {
                            "$lte": [
                              "$$i.price_snapshot",
                              {
                                "$numberDecimal": "9.999999999999999999999999999999999E+6144"
                              }
                            ]
                          },
                          {
                            "$eq": [
                              "$$i.price_snapshot",
                              {
                                "$round": [
                                  "$$i.price_snapshot",
                                  2
                                ]
                              }
                            ]
                          }
                        ]
                      }
                    }
                  }
                ]
              }
            }
          ]
        },
        "validationLevel": "strict",
        "validationAction": "error"
      },
      "indexes": [
        {
          "v": 2,
          "key": {
            "_id": 1
          },
          "name": "_id_"
        },
        {
          "v": 2,
          "key": {
            "user_id": 1
          },
          "name": "uq_carts_user_id_active",
          "unique": true,
          "partialFilterExpression": {
            "status": "active"
          }
        },
        {
          "v": 2,
          "key": {
            "user_id": 1,
            "status": 1
          },
          "name": "idx_carts_user_id_status"
        },
        {
          "v": 2,
          "key": {
            "status": 1,
            "updated_at": 1
          },
          "name": "idx_carts_status_updated_at"
        },
        {
          "v": 2,
          "key": {
            "updated_at": 1
          },
          "name": "idx_carts_updated_at"
        }
      ]
    },
    {
      "collection": "orders",
      "count": 0,
      "conforming_documents": 0,
      "options": {
        "validator": {
          "$jsonSchema": {
            "bsonType": "object",
            "required": [
              "_id",
              "schema_version",
              "user_id",
              "order_number",
              "status",
              "payment_status",
              "shipping_status",
              "subtotal",
              "shipping_fee",
              "total_amount",
              "ordered_at",
              "completed_at",
              "checkout_id",
              "request_hash",
              "is_demo",
              "currency",
              "paid_at",
              "discount_amount",
              "created_at",
              "updated_at"
            ],
            "properties": {
              "_id": {
                "bsonType": "objectId"
              },
              "schema_version": {
                "bsonType": "int",
                "enum": [
                  4
                ]
              },
              "user_id": {
                "bsonType": "objectId"
              },
              "order_number": {
                "bsonType": "string",
                "maxLength": 100,
                "minLength": 1
              },
              "status": {
                "enum": [
                  "pending",
                  "confirmed",
                  "shipping",
                  "completed",
                  "cancelled"
                ]
              },
              "payment_status": {
                "enum": [
                  "unpaid",
                  "paid",
                  "failed",
                  "refunded"
                ]
              },
              "shipping_status": {
                "enum": [
                  "pending",
                  "processing",
                  "shipped",
                  "delivered",
                  "returned",
                  "cancelled"
                ]
              },
              "subtotal": {
                "bsonType": "decimal",
                "minimum": {
                  "$numberDecimal": "0"
                }
              },
              "shipping_fee": {
                "bsonType": "decimal",
                "minimum": {
                  "$numberDecimal": "0"
                }
              },
              "total_amount": {
                "bsonType": "decimal",
                "minimum": {
                  "$numberDecimal": "0"
                }
              },
              "ordered_at": {
                "bsonType": "date"
              },
              "completed_at": {
                "bsonType": [
                  "date",
                  "null"
                ]
              },
              "checkout_id": {
                "bsonType": "string",
                "maxLength": 128,
                "minLength": 1
              },
              "request_hash": {
                "bsonType": "string",
                "pattern": "^[a-f0-9]{64}$",
                "maxLength": 64,
                "minLength": 64
              },
              "is_demo": {
                "bsonType": "bool"
              },
              "currency": {
                "enum": [
                  "TWD"
                ]
              },
              "paid_at": {
                "bsonType": [
                  "date",
                  "null"
                ]
              },
              "discount_amount": {
                "bsonType": "decimal",
                "minimum": {
                  "$numberDecimal": "0"
                }
              },
              "created_at": {
                "bsonType": "date"
              },
              "updated_at": {
                "bsonType": "date"
              }
            },
            "additionalProperties": false
          },
          "$and": [
            {
              "$expr": {
                "$eq": [
                  "$total_amount",
                  {
                    "$add": [
                      {
                        "$subtract": [
                          "$subtotal",
                          "$discount_amount"
                        ]
                      },
                      "$shipping_fee"
                    ]
                  }
                ]
              }
            },
            {
              "$expr": {
                "$lte": [
                  "$discount_amount",
                  "$subtotal"
                ]
              }
            },
            {
              "$expr": {
                "$or": [
                  {
                    "$not": [
                      {
                        "$eq": [
                          "$payment_status",
                          "paid"
                        ]
                      }
                    ]
                  },
                  {
                    "$ne": [
                      "$paid_at",
                      null
                    ]
                  }
                ]
              }
            },
            {
              "$expr": {
                "$or": [
                  {
                    "$not": [
                      {
                        "$eq": [
                          "$status",
                          "completed"
                        ]
                      }
                    ]
                  },
                  {
                    "$ne": [
                      "$completed_at",
                      null
                    ]
                  }
                ]
              }
            },
            {
              "$expr": {
                "$and": [
                  {
                    "$lte": [
                      "$subtotal",
                      {
                        "$numberDecimal": "9.999999999999999999999999999999999E+6144"
                      }
                    ]
                  },
                  {
                    "$eq": [
                      "$subtotal",
                      {
                        "$round": [
                          "$subtotal",
                          2
                        ]
                      }
                    ]
                  }
                ]
              }
            },
            {
              "$expr": {
                "$and": [
                  {
                    "$lte": [
                      "$shipping_fee",
                      {
                        "$numberDecimal": "9.999999999999999999999999999999999E+6144"
                      }
                    ]
                  },
                  {
                    "$eq": [
                      "$shipping_fee",
                      {
                        "$round": [
                          "$shipping_fee",
                          2
                        ]
                      }
                    ]
                  }
                ]
              }
            },
            {
              "$expr": {
                "$and": [
                  {
                    "$lte": [
                      "$total_amount",
                      {
                        "$numberDecimal": "9.999999999999999999999999999999999E+6144"
                      }
                    ]
                  },
                  {
                    "$eq": [
                      "$total_amount",
                      {
                        "$round": [
                          "$total_amount",
                          2
                        ]
                      }
                    ]
                  }
                ]
              }
            },
            {
              "$expr": {
                "$and": [
                  {
                    "$lte": [
                      "$discount_amount",
                      {
                        "$numberDecimal": "9.999999999999999999999999999999999E+6144"
                      }
                    ]
                  },
                  {
                    "$eq": [
                      "$discount_amount",
                      {
                        "$round": [
                          "$discount_amount",
                          2
                        ]
                      }
                    ]
                  }
                ]
              }
            }
          ]
        },
        "validationLevel": "strict",
        "validationAction": "error"
      },
      "indexes": [
        {
          "v": 2,
          "key": {
            "_id": 1
          },
          "name": "_id_"
        },
        {
          "v": 2,
          "key": {
            "order_number": 1
          },
          "name": "uq_orders_order_number",
          "unique": true
        },
        {
          "v": 2,
          "key": {
            "user_id": 1,
            "checkout_id": 1
          },
          "name": "uq_orders_user_id_checkout_id",
          "unique": true
        },
        {
          "v": 2,
          "key": {
            "user_id": 1,
            "ordered_at": -1
          },
          "name": "idx_orders_user_id_ordered_at"
        },
        {
          "v": 2,
          "key": {
            "status": 1,
            "ordered_at": -1
          },
          "name": "idx_orders_status_ordered_at"
        },
        {
          "v": 2,
          "key": {
            "is_demo": 1,
            "payment_status": 1,
            "ordered_at": -1
          },
          "name": "idx_orders_is_demo_payment_status_ordered_at"
        }
      ]
    },
    {
      "collection": "user_events",
      "count": 0,
      "conforming_documents": 0,
      "options": {
        "validator": {
          "$jsonSchema": {
            "bsonType": "object",
            "required": [
              "_id",
              "schema_version",
              "event_id",
              "user_id",
              "session_id",
              "event_type",
              "product_id",
              "order_id",
              "recommendation_id",
              "search_query",
              "event_metadata",
              "created_at"
            ],
            "properties": {
              "_id": {
                "bsonType": "objectId"
              },
              "schema_version": {
                "bsonType": "int",
                "enum": [
                  2
                ]
              },
              "event_id": {
                "bsonType": "string",
                "minLength": 1
              },
              "user_id": {
                "bsonType": [
                  "objectId",
                  "null"
                ]
              },
              "session_id": {
                "bsonType": "string",
                "maxLength": 128,
                "minLength": 1
              },
              "event_type": {
                "enum": [
                  "product_view",
                  "product_search",
                  "add_to_cart",
                  "remove_from_cart",
                  "purchase",
                  "recommendation_impression",
                  "recommendation_click"
                ]
              },
              "product_id": {
                "bsonType": [
                  "objectId",
                  "null"
                ]
              },
              "order_id": {
                "bsonType": [
                  "objectId",
                  "null"
                ]
              },
              "recommendation_id": {
                "bsonType": [
                  "objectId",
                  "null"
                ]
              },
              "search_query": {
                "bsonType": [
                  "string",
                  "null"
                ],
                "maxLength": 200,
                "minLength": 1
              },
              "event_metadata": {
                "bsonType": "object"
              },
              "created_at": {
                "bsonType": "date"
              }
            },
            "additionalProperties": false
          },
          "$and": [
            {
              "$expr": {
                "$or": [
                  {
                    "$not": [
                      {
                        "$in": [
                          "$event_type",
                          [
                            "product_view",
                            "add_to_cart",
                            "remove_from_cart"
                          ]
                        ]
                      }
                    ]
                  },
                  {
                    "$ne": [
                      "$product_id",
                      null
                    ]
                  }
                ]
              }
            },
            {
              "$expr": {
                "$or": [
                  {
                    "$not": [
                      {
                        "$in": [
                          "$event_type",
                          [
                            "purchase"
                          ]
                        ]
                      }
                    ]
                  },
                  {
                    "$ne": [
                      "$order_id",
                      null
                    ]
                  }
                ]
              }
            },
            {
              "$expr": {
                "$or": [
                  {
                    "$not": [
                      {
                        "$in": [
                          "$event_type",
                          [
                            "recommendation_impression",
                            "recommendation_click"
                          ]
                        ]
                      }
                    ]
                  },
                  {
                    "$ne": [
                      "$recommendation_id",
                      null
                    ]
                  }
                ]
              }
            },
            {
              "$expr": {
                "$or": [
                  {
                    "$not": [
                      {
                        "$in": [
                          "$event_type",
                          [
                            "product_search"
                          ]
                        ]
                      }
                    ]
                  },
                  {
                    "$ne": [
                      "$search_query",
                      null
                    ]
                  }
                ]
              }
            },
            {
              "$expr": {
                "$lte": [
                  {
                    "$bsonSize": "$event_metadata"
                  },
                  2048
                ]
              }
            },
            {
              "$expr": {
                "$or": [
                  {
                    "$not": [
                      {
                        "$eq": [
                          "$event_type",
                          "recommendation_click"
                        ]
                      }
                    ]
                  },
                  {
                    "$ne": [
                      "$product_id",
                      null
                    ]
                  }
                ]
              }
            }
          ]
        },
        "validationLevel": "strict",
        "validationAction": "error"
      },
      "indexes": [
        {
          "v": 2,
          "key": {
            "_id": 1
          },
          "name": "_id_"
        },
        {
          "v": 2,
          "key": {
            "event_id": 1
          },
          "name": "uq_user_events_event_id",
          "unique": true
        },
        {
          "v": 2,
          "key": {
            "order_id": 1
          },
          "name": "uq_user_events_order_id_purchase",
          "unique": true,
          "partialFilterExpression": {
            "event_type": "purchase",
            "order_id": {
              "$type": "objectId"
            }
          }
        },
        {
          "v": 2,
          "key": {
            "user_id": 1,
            "event_type": 1,
            "created_at": -1
          },
          "name": "idx_user_events_user_id_event_type_created_at"
        },
        {
          "v": 2,
          "key": {
            "recommendation_id": 1,
            "event_type": 1
          },
          "name": "idx_user_events_recommendation_id_event_type"
        }
      ]
    },
    {
      "collection": "ai_requests",
      "count": 0,
      "conforming_documents": 0,
      "options": {
        "validator": {
          "$jsonSchema": {
            "bsonType": "object",
            "required": [
              "_id",
              "schema_version",
              "user_id",
              "parent_request_id",
              "task_type",
              "execution_mode",
              "requested_provider",
              "actual_provider",
              "model_name",
              "model_revision",
              "prompt_name",
              "prompt_version",
              "status",
              "is_success",
              "input_text",
              "output_text",
              "input_summary",
              "parameters",
              "latency_ms",
              "input_tokens",
              "output_tokens",
              "token_count",
              "estimated_cost",
              "cost_currency",
              "is_cache_hit",
              "fallback_reason",
              "error_code",
              "started_at",
              "completed_at",
              "created_at"
            ],
            "properties": {
              "_id": {
                "bsonType": "objectId"
              },
              "schema_version": {
                "bsonType": "int",
                "enum": [
                  2
                ]
              },
              "user_id": {
                "bsonType": [
                  "objectId",
                  "null"
                ]
              },
              "parent_request_id": {
                "bsonType": [
                  "objectId",
                  "null"
                ]
              },
              "task_type": {
                "enum": [
                  "product_embedding",
                  "product_recommendation",
                  "sales_summary"
                ]
              },
              "execution_mode": {
                "enum": [
                  "local",
                  "api",
                  "hybrid",
                  "baseline"
                ]
              },
              "requested_provider": {
                "enum": [
                  "huggingface",
                  "anthropic",
                  "rules",
                  "pipeline"
                ]
              },
              "actual_provider": {
                "enum": [
                  "huggingface",
                  "anthropic",
                  "rules",
                  "pipeline",
                  null
                ]
              },
              "model_name": {
                "bsonType": [
                  "string",
                  "null"
                ]
              },
              "model_revision": {
                "bsonType": [
                  "string",
                  "null"
                ]
              },
              "prompt_name": {
                "bsonType": [
                  "string",
                  "null"
                ]
              },
              "prompt_version": {
                "bsonType": [
                  "string",
                  "null"
                ]
              },
              "status": {
                "enum": [
                  "queued",
                  "running",
                  "succeeded",
                  "failed",
                  "timeout"
                ]
              },
              "is_success": {
                "bsonType": [
                  "bool",
                  "null"
                ]
              },
              "input_text": {
                "bsonType": [
                  "string",
                  "null"
                ],
                "maxLength": 8000
              },
              "output_text": {
                "bsonType": [
                  "string",
                  "null"
                ],
                "maxLength": 8000
              },
              "input_summary": {
                "bsonType": "object"
              },
              "parameters": {
                "bsonType": "object"
              },
              "latency_ms": {
                "bsonType": [
                  "int",
                  "null"
                ],
                "minimum": 0
              },
              "input_tokens": {
                "bsonType": [
                  "int",
                  "null"
                ],
                "minimum": 0
              },
              "output_tokens": {
                "bsonType": [
                  "int",
                  "null"
                ],
                "minimum": 0
              },
              "token_count": {
                "bsonType": [
                  "int",
                  "null"
                ],
                "minimum": 0
              },
              "estimated_cost": {
                "bsonType": [
                  "decimal",
                  "null"
                ],
                "minimum": {
                  "$numberDecimal": "0"
                }
              },
              "cost_currency": {
                "enum": [
                  "USD",
                  null
                ]
              },
              "is_cache_hit": {
                "bsonType": "bool"
              },
              "fallback_reason": {
                "bsonType": [
                  "string",
                  "null"
                ]
              },
              "error_code": {
                "bsonType": [
                  "string",
                  "null"
                ]
              },
              "started_at": {
                "bsonType": [
                  "date",
                  "null"
                ]
              },
              "completed_at": {
                "bsonType": [
                  "date",
                  "null"
                ]
              },
              "created_at": {
                "bsonType": "date"
              }
            },
            "additionalProperties": false
          },
          "$and": [
            {
              "$expr": {
                "$lte": [
                  {
                    "$bsonSize": "$input_summary"
                  },
                  8192
                ]
              }
            },
            {
              "$expr": {
                "$or": [
                  {
                    "$and": [
                      {
                        "$in": [
                          "$status",
                          [
                            "queued",
                            "running"
                          ]
                        ]
                      },
                      {
                        "$eq": [
                          "$is_success",
                          null
                        ]
                      }
                    ]
                  },
                  {
                    "$and": [
                      {
                        "$in": [
                          "$status",
                          [
                            "succeeded",
                            "failed",
                            "timeout"
                          ]
                        ]
                      },
                      {
                        "$eq": [
                          "$is_success",
                          {
                            "$eq": [
                              "$status",
                              "succeeded"
                            ]
                          }
                        ]
                      },
                      {
                        "$ne": [
                          "$latency_ms",
                          null
                        ]
                      },
                      {
                        "$ne": [
                          "$completed_at",
                          null
                        ]
                      }
                    ]
                  }
                ]
              }
            },
            {
              "$expr": {
                "$or": [
                  {
                    "$eq": [
                      "$estimated_cost",
                      null
                    ]
                  },
                  {
                    "$eq": [
                      "$cost_currency",
                      "USD"
                    ]
                  }
                ]
              }
            },
            {
              "$expr": {
                "$or": [
                  {
                    "$eq": [
                      "$estimated_cost",
                      null
                    ]
                  },
                  {
                    "$lte": [
                      "$estimated_cost",
                      {
                        "$numberDecimal": "9.999999999999999999999999999999999E+6144"
                      }
                    ]
                  }
                ]
              }
            },
            {
              "$expr": {
                "$or": [
                  {
                    "$not": [
                      {
                        "$eq": [
                          "$status",
                          "running"
                        ]
                      }
                    ]
                  },
                  {
                    "$ne": [
                      "$started_at",
                      null
                    ]
                  }
                ]
              }
            },
            {
              "$expr": {
                "$or": [
                  {
                    "$not": [
                      {
                        "$eq": [
                          "$status",
                          "succeeded"
                        ]
                      }
                    ]
                  },
                  {
                    "$and": [
                      {
                        "$ne": [
                          "$started_at",
                          null
                        ]
                      },
                      {
                        "$ne": [
                          "$actual_provider",
                          null
                        ]
                      }
                    ]
                  }
                ]
              }
            },
            {
              "$expr": {
                "$or": [
                  {
                    "$not": [
                      {
                        "$and": [
                          {
                            "$ne": [
                              "$started_at",
                              null
                            ]
                          },
                          {
                            "$in": [
                              "$actual_provider",
                              [
                                "huggingface",
                                "anthropic"
                              ]
                            ]
                          }
                        ]
                      }
                    ]
                  },
                  {
                    "$and": [
                      {
                        "$and": [
                          {
                            "$ne": [
                              "$model_name",
                              null
                            ]
                          },
                          {
                            "$ne": [
                              "$model_name",
                              ""
                            ]
                          }
                        ]
                      },
                      {
                        "$and": [
                          {
                            "$ne": [
                              "$model_revision",
                              null
                            ]
                          },
                          {
                            "$ne": [
                              "$model_revision",
                              ""
                            ]
                          }
                        ]
                      }
                    ]
                  }
                ]
              }
            },
            {
              "$expr": {
                "$or": [
                  {
                    "$not": [
                      {
                        "$and": [
                          {
                            "$eq": [
                              "$task_type",
                              "sales_summary"
                            ]
                          },
                          {
                            "$eq": [
                              "$actual_provider",
                              "anthropic"
                            ]
                          },
                          {
                            "$ne": [
                              "$started_at",
                              null
                            ]
                          }
                        ]
                      }
                    ]
                  },
                  {
                    "$and": [
                      {
                        "$and": [
                          {
                            "$ne": [
                              "$prompt_name",
                              null
                            ]
                          },
                          {
                            "$ne": [
                              "$prompt_name",
                              ""
                            ]
                          }
                        ]
                      },
                      {
                        "$and": [
                          {
                            "$ne": [
                              "$prompt_version",
                              null
                            ]
                          },
                          {
                            "$ne": [
                              "$prompt_version",
                              ""
                            ]
                          }
                        ]
                      }
                    ]
                  }
                ]
              }
            }
          ]
        },
        "validationLevel": "strict",
        "validationAction": "error"
      },
      "indexes": [
        {
          "v": 2,
          "key": {
            "_id": 1
          },
          "name": "_id_"
        },
        {
          "v": 2,
          "key": {
            "task_type": 1,
            "actual_provider": 1,
            "created_at": -1
          },
          "name": "idx_ai_requests_task_type_actual_provider_created_at"
        },
        {
          "v": 2,
          "key": {
            "parent_request_id": 1
          },
          "name": "idx_ai_requests_parent_request_id"
        }
      ]
    },
    {
      "collection": "product_embeddings",
      "count": 0,
      "conforming_documents": 0,
      "options": {
        "validator": {
          "$jsonSchema": {
            "bsonType": "object",
            "required": [
              "_id",
              "schema_version",
              "product_id",
              "model",
              "revision",
              "vector",
              "dimension",
              "content_hash",
              "preprocessing_version",
              "is_normalized",
              "created_at",
              "updated_at"
            ],
            "properties": {
              "_id": {
                "bsonType": "objectId"
              },
              "schema_version": {
                "bsonType": "int",
                "enum": [
                  2
                ]
              },
              "product_id": {
                "bsonType": "objectId"
              },
              "model": {
                "enum": [
                  "BAAI/bge-small-zh-v1.5"
                ]
              },
              "revision": {
                "bsonType": "string",
                "minLength": 1
              },
              "vector": {
                "bsonType": "array",
                "items": {
                  "bsonType": "double",
                  "minimum": -1.7976931348623157e+308,
                  "maximum": 1.7976931348623157e+308
                },
                "minItems": 512,
                "maxItems": 512,
                "uniqueItems": false
              },
              "dimension": {
                "bsonType": "int",
                "enum": [
                  512
                ]
              },
              "content_hash": {
                "bsonType": "string",
                "pattern": "^[a-f0-9]{64}$",
                "maxLength": 64,
                "minLength": 64
              },
              "preprocessing_version": {
                "bsonType": "string",
                "minLength": 1
              },
              "is_normalized": {
                "bsonType": "bool"
              },
              "created_at": {
                "bsonType": "date"
              },
              "updated_at": {
                "bsonType": "date"
              }
            },
            "additionalProperties": false
          },
          "$and": [
            {
              "$expr": {
                "$anyElementTrue": [
                  {
                    "$map": {
                      "input": "$vector",
                      "as": "v",
                      "in": {
                        "$ne": [
                          "$$v",
                          0
                        ]
                      }
                    }
                  }
                ]
              }
            }
          ]
        },
        "validationLevel": "strict",
        "validationAction": "error"
      },
      "indexes": [
        {
          "v": 2,
          "key": {
            "_id": 1
          },
          "name": "_id_"
        },
        {
          "v": 2,
          "key": {
            "product_id": 1,
            "model": 1
          },
          "name": "uq_product_embeddings_product_id_model",
          "unique": true
        }
      ]
    },
    {
      "collection": "recommendations",
      "count": 0,
      "conforming_documents": 0,
      "options": {
        "validator": {
          "$jsonSchema": {
            "bsonType": "object",
            "required": [
              "_id",
              "schema_version",
              "user_id",
              "session_id",
              "source_product_id",
              "ai_request_id",
              "strategy",
              "model",
              "revision",
              "items",
              "created_at"
            ],
            "properties": {
              "_id": {
                "bsonType": "objectId"
              },
              "schema_version": {
                "bsonType": "int",
                "enum": [
                  2
                ]
              },
              "user_id": {
                "bsonType": [
                  "objectId",
                  "null"
                ]
              },
              "session_id": {
                "bsonType": "string",
                "maxLength": 128,
                "minLength": 1
              },
              "source_product_id": {
                "bsonType": [
                  "objectId",
                  "null"
                ]
              },
              "ai_request_id": {
                "bsonType": "objectId"
              },
              "strategy": {
                "enum": [
                  "baseline",
                  "bge_similar",
                  "bge_personalized"
                ]
              },
              "model": {
                "bsonType": [
                  "string",
                  "null"
                ]
              },
              "revision": {
                "bsonType": [
                  "string",
                  "null"
                ]
              },
              "items": {
                "bsonType": "array",
                "items": {
                  "bsonType": "object",
                  "required": [
                    "product_id",
                    "rank",
                    "score",
                    "reason"
                  ],
                  "properties": {
                    "product_id": {
                      "bsonType": "objectId"
                    },
                    "rank": {
                      "bsonType": "int",
                      "minimum": 1,
                      "maximum": 10
                    },
                    "score": {
                      "bsonType": "double",
                      "minimum": -1.7976931348623157e+308,
                      "maximum": 1.7976931348623157e+308
                    },
                    "reason": {
                      "bsonType": "string",
                      "maxLength": 500,
                      "minLength": 1
                    }
                  },
                  "additionalProperties": false
                },
                "minItems": 0,
                "maxItems": 10,
                "uniqueItems": false
              },
              "created_at": {
                "bsonType": "date"
              }
            },
            "additionalProperties": false
          },
          "$and": [
            {
              "$expr": {
                "$eq": [
                  {
                    "$size": "$items"
                  },
                  {
                    "$size": {
                      "$setUnion": [
                        "$items.product_id",
                        []
                      ]
                    }
                  }
                ]
              }
            },
            {
              "$expr": {
                "$eq": [
                  "$items.rank",
                  {
                    "$range": [
                      1,
                      {
                        "$add": [
                          {
                            "$size": "$items"
                          },
                          1
                        ]
                      }
                    ]
                  }
                ]
              }
            },
            {
              "$expr": {
                "$or": [
                  {
                    "$eq": [
                      "$strategy",
                      "baseline"
                    ]
                  },
                  {
                    "$and": [
                      {
                        "$ne": [
                          "$model",
                          null
                        ]
                      },
                      {
                        "$ne": [
                          "$revision",
                          null
                        ]
                      },
                      {
                        "$allElementsTrue": [
                          {
                            "$map": {
                              "input": "$items",
                              "as": "i",
                              "in": {
                                "$and": [
                                  {
                                    "$gte": [
                                      "$$i.score",
                                      -1
                                    ]
                                  },
                                  {
                                    "$lte": [
                                      "$$i.score",
                                      1
                                    ]
                                  }
                                ]
                              }
                            }
                          }
                        ]
                      }
                    ]
                  }
                ]
              }
            },
            {
              "$expr": {
                "$or": [
                  {
                    "$ne": [
                      "$strategy",
                      "bge_similar"
                    ]
                  },
                  {
                    "$ne": [
                      "$source_product_id",
                      null
                    ]
                  }
                ]
              }
            },
            {
              "$expr": {
                "$or": [
                  {
                    "$not": [
                      {
                        "$in": [
                          "$strategy",
                          [
                            "bge_similar",
                            "bge_personalized"
                          ]
                        ]
                      }
                    ]
                  },
                  {
                    "$and": [
                      {
                        "$and": [
                          {
                            "$ne": [
                              "$model",
                              null
                            ]
                          },
                          {
                            "$ne": [
                              "$model",
                              ""
                            ]
                          }
                        ]
                      },
                      {
                        "$and": [
                          {
                            "$ne": [
                              "$revision",
                              null
                            ]
                          },
                          {
                            "$ne": [
                              "$revision",
                              ""
                            ]
                          }
                        ]
                      }
                    ]
                  }
                ]
              }
            }
          ]
        },
        "validationLevel": "strict",
        "validationAction": "error"
      },
      "indexes": [
        {
          "v": 2,
          "key": {
            "_id": 1
          },
          "name": "_id_"
        },
        {
          "v": 2,
          "key": {
            "user_id": 1,
            "created_at": -1
          },
          "name": "idx_recommendations_user_id_created_at"
        }
      ]
    },
    {
      "collection": "ai_insights",
      "count": 0,
      "conforming_documents": 0,
      "options": {
        "validator": {
          "$jsonSchema": {
            "bsonType": "object",
            "required": [
              "_id",
              "schema_version",
              "ai_request_id",
              "task_type",
              "period_start",
              "period_end",
              "report_timezone",
              "is_demo",
              "input_summary",
              "text",
              "model",
              "prompt_version",
              "usage",
              "elapsed_ms",
              "expires_at",
              "created_at"
            ],
            "properties": {
              "_id": {
                "bsonType": "string",
                "minLength": 1
              },
              "schema_version": {
                "bsonType": "int",
                "enum": [
                  2
                ]
              },
              "ai_request_id": {
                "bsonType": "objectId"
              },
              "task_type": {
                "enum": [
                  "sales_summary"
                ]
              },
              "period_start": {
                "bsonType": "date"
              },
              "period_end": {
                "bsonType": "date"
              },
              "report_timezone": {
                "enum": [
                  "Asia/Taipei"
                ]
              },
              "is_demo": {
                "enum": [
                  true
                ]
              },
              "input_summary": {
                "bsonType": "object"
              },
              "text": {
                "bsonType": "string",
                "maxLength": 8000,
                "minLength": 1
              },
              "model": {
                "bsonType": "string",
                "minLength": 1
              },
              "prompt_version": {
                "bsonType": "string",
                "minLength": 1
              },
              "usage": {
                "bsonType": "object"
              },
              "elapsed_ms": {
                "bsonType": [
                  "int",
                  "null"
                ],
                "minimum": 0
              },
              "expires_at": {
                "bsonType": "date"
              },
              "created_at": {
                "bsonType": "date"
              }
            },
            "additionalProperties": false
          },
          "$and": [
            {
              "$expr": {
                "$lt": [
                  "$period_start",
                  "$period_end"
                ]
              }
            },
            {
              "$expr": {
                "$lte": [
                  {
                    "$bsonSize": "$input_summary"
                  },
                  8192
                ]
              }
            }
          ]
        },
        "validationLevel": "strict",
        "validationAction": "error"
      },
      "indexes": [
        {
          "v": 2,
          "key": {
            "_id": 1
          },
          "name": "_id_"
        },
        {
          "v": 2,
          "key": {
            "expires_at": 1
          },
          "name": "ttl_ai_insights_expires_at",
          "expireAfterSeconds": 0
        }
      ]
    },
    {
      "collection": "ai_usage",
      "count": 0,
      "conforming_documents": 0,
      "options": {
        "validator": {
          "$jsonSchema": {
            "bsonType": "object",
            "required": [
              "_id",
              "schema_version",
              "count",
              "updated_at"
            ],
            "properties": {
              "_id": {
                "bsonType": "string",
                "minLength": 1
              },
              "schema_version": {
                "bsonType": "int",
                "enum": [
                  2
                ]
              },
              "count": {
                "bsonType": "int",
                "minimum": 0
              },
              "updated_at": {
                "bsonType": "date"
              }
            },
            "additionalProperties": false
          }
        },
        "validationLevel": "strict",
        "validationAction": "error"
      },
      "indexes": [
        {
          "v": 2,
          "key": {
            "_id": 1
          },
          "name": "_id_"
        }
      ]
    },
    {
      "collection": "request_limits",
      "count": 0,
      "conforming_documents": 0,
      "options": {
        "validator": {
          "$jsonSchema": {
            "bsonType": "object",
            "required": [
              "_id",
              "schema_version",
              "count",
              "expires_at"
            ],
            "properties": {
              "_id": {
                "bsonType": "string",
                "minLength": 1
              },
              "schema_version": {
                "bsonType": "int",
                "enum": [
                  2
                ]
              },
              "count": {
                "bsonType": "int",
                "minimum": 0
              },
              "expires_at": {
                "bsonType": "date"
              }
            },
            "additionalProperties": false
          }
        },
        "validationLevel": "strict",
        "validationAction": "error"
      },
      "indexes": [
        {
          "v": 2,
          "key": {
            "_id": 1
          },
          "name": "_id_"
        },
        {
          "v": 2,
          "key": {
            "expires_at": 1
          },
          "name": "ttl_request_limits_expires_at",
          "expireAfterSeconds": 0
        }
      ]
    },
    {
      "collection": "schema_migrations",
      "count": 4,
      "conforming_documents": 4,
      "options": {
        "validator": {
          "$jsonSchema": {
            "bsonType": "object",
            "required": [
              "_id",
              "schema_version",
              "checksum",
              "status",
              "started_at",
              "completed_at",
              "counts",
              "error_code"
            ],
            "properties": {
              "_id": {
                "bsonType": "string",
                "minLength": 1
              },
              "schema_version": {
                "bsonType": "int",
                "enum": [
                  2
                ]
              },
              "checksum": {
                "bsonType": "string",
                "pattern": "^[a-f0-9]{64}$",
                "maxLength": 64,
                "minLength": 64
              },
              "status": {
                "enum": [
                  "running",
                  "succeeded",
                  "failed"
                ]
              },
              "started_at": {
                "bsonType": "date"
              },
              "completed_at": {
                "bsonType": [
                  "date",
                  "null"
                ]
              },
              "counts": {
                "bsonType": "object",
                "required": [
                  "source",
                  "target",
                  "errors"
                ],
                "properties": {
                  "source": {
                    "bsonType": "int",
                    "minimum": 0
                  },
                  "target": {
                    "bsonType": "int",
                    "minimum": 0
                  },
                  "errors": {
                    "bsonType": "int",
                    "minimum": 0
                  }
                },
                "additionalProperties": false
              },
              "error_code": {
                "bsonType": [
                  "string",
                  "null"
                ]
              }
            },
            "additionalProperties": false
          }
        },
        "validationLevel": "strict",
        "validationAction": "error"
      },
      "indexes": [
        {
          "v": 2,
          "key": {
            "_id": 1
          },
          "name": "_id_"
        }
      ]
    },
    {
      "collection": "cart_events",
      "count": 0,
      "conforming_documents": 0,
      "options": {
        "validator": {
          "$jsonSchema": {
            "bsonType": "object",
            "required": [
              "_id",
              "schema_version",
              "cart_id",
              "user_id",
              "operation_id",
              "request_hash",
              "event_type",
              "product_id",
              "quantity_before",
              "quantity_after",
              "price_snapshot",
              "event_at",
              "metadata",
              "event_id",
              "sku_id",
              "created_at"
            ],
            "properties": {
              "_id": {
                "bsonType": "objectId"
              },
              "schema_version": {
                "bsonType": "int",
                "enum": [
                  4
                ]
              },
              "cart_id": {
                "bsonType": "objectId"
              },
              "user_id": {
                "bsonType": "objectId"
              },
              "operation_id": {
                "bsonType": "string",
                "maxLength": 128,
                "minLength": 1
              },
              "request_hash": {
                "bsonType": "string",
                "pattern": "^[a-f0-9]{64}$",
                "maxLength": 64,
                "minLength": 64
              },
              "event_type": {
                "bsonType": "string",
                "pattern": "^[A-Z][A-Z0-9_]*$",
                "maxLength": 40,
                "minLength": 1
              },
              "product_id": {
                "bsonType": [
                  "objectId",
                  "null"
                ]
              },
              "quantity_before": {
                "bsonType": [
                  "int",
                  "null"
                ],
                "minimum": 0,
                "maximum": 99
              },
              "quantity_after": {
                "bsonType": [
                  "int",
                  "null"
                ],
                "minimum": 0,
                "maximum": 99
              },
              "price_snapshot": {
                "bsonType": [
                  "decimal",
                  "null"
                ],
                "minimum": {
                  "$numberDecimal": "0"
                }
              },
              "event_at": {
                "bsonType": "date"
              },
              "metadata": {
                "bsonType": "object"
              },
              "event_id": {
                "bsonType": "string",
                "maxLength": 128,
                "minLength": 1
              },
              "sku_id": {
                "bsonType": [
                  "objectId",
                  "null"
                ]
              },
              "created_at": {
                "bsonType": "date"
              }
            },
            "additionalProperties": false
          },
          "$and": [
            {
              "$expr": {
                "$or": [
                  {
                    "$eq": [
                      "$price_snapshot",
                      null
                    ]
                  },
                  {
                    "$and": [
                      {
                        "$lte": [
                          "$price_snapshot",
                          {
                            "$numberDecimal": "1.000000000000000000000000000000000E+6144"
                          }
                        ]
                      },
                      {
                        "$eq": [
                          "$price_snapshot",
                          {
                            "$round": [
                              "$price_snapshot",
                              2
                            ]
                          }
                        ]
                      }
                    ]
                  }
                ]
              }
            },
            {
              "$expr": {
                "$lte": [
                  {
                    "$bsonSize": "$metadata"
                  },
                  2048
                ]
              }
            },
            {
              "$expr": {
                "$or": [
                  {
                    "$ne": [
                      "$event_type",
                      "ADD"
                    ]
                  },
                  {
                    "$and": [
                      {
                        "$and": [
                          {
                            "$ne": [
                              "$product_id",
                              null
                            ]
                          },
                          {
                            "$ne": [
                              "$quantity_before",
                              null
                            ]
                          },
                          {
                            "$ne": [
                              "$quantity_after",
                              null
                            ]
                          },
                          {
                            "$ne": [
                              "$price_snapshot",
                              null
                            ]
                          }
                        ]
                      },
                      {
                        "$gt": [
                          "$quantity_after",
                          "$quantity_before"
                        ]
                      }
                    ]
                  }
                ]
              }
            },
            {
              "$expr": {
                "$or": [
                  {
                    "$ne": [
                      "$event_type",
                      "REMOVE"
                    ]
                  },
                  {
                    "$and": [
                      {
                        "$and": [
                          {
                            "$ne": [
                              "$product_id",
                              null
                            ]
                          },
                          {
                            "$ne": [
                              "$quantity_before",
                              null
                            ]
                          },
                          {
                            "$ne": [
                              "$quantity_after",
                              null
                            ]
                          },
                          {
                            "$ne": [
                              "$price_snapshot",
                              null
                            ]
                          }
                        ]
                      },
                      {
                        "$gt": [
                          "$quantity_before",
                          0
                        ]
                      },
                      {
                        "$eq": [
                          "$quantity_after",
                          0
                        ]
                      }
                    ]
                  }
                ]
              }
            },
            {
              "$expr": {
                "$or": [
                  {
                    "$ne": [
                      "$event_type",
                      "QTY_CHANGE"
                    ]
                  },
                  {
                    "$and": [
                      {
                        "$and": [
                          {
                            "$ne": [
                              "$product_id",
                              null
                            ]
                          },
                          {
                            "$ne": [
                              "$quantity_before",
                              null
                            ]
                          },
                          {
                            "$ne": [
                              "$quantity_after",
                              null
                            ]
                          },
                          {
                            "$ne": [
                              "$price_snapshot",
                              null
                            ]
                          }
                        ]
                      },
                      {
                        "$gt": [
                          "$quantity_before",
                          0
                        ]
                      },
                      {
                        "$gt": [
                          "$quantity_after",
                          0
                        ]
                      },
                      {
                        "$ne": [
                          "$quantity_before",
                          "$quantity_after"
                        ]
                      }
                    ]
                  }
                ]
              }
            },
            {
              "$expr": {
                "$or": [
                  {
                    "$ne": [
                      "$event_type",
                      "CHECKOUT"
                    ]
                  },
                  {
                    "$and": [
                      {
                        "$eq": [
                          "$product_id",
                          null
                        ]
                      },
                      {
                        "$eq": [
                          "$quantity_before",
                          null
                        ]
                      },
                      {
                        "$eq": [
                          "$quantity_after",
                          null
                        ]
                      },
                      {
                        "$eq": [
                          "$price_snapshot",
                          null
                        ]
                      }
                    ]
                  }
                ]
              }
            },
            {
              "$expr": {
                "$or": [
                  {
                    "$ne": [
                      "$event_type",
                      "ABANDON"
                    ]
                  },
                  {
                    "$and": [
                      {
                        "$eq": [
                          "$product_id",
                          null
                        ]
                      },
                      {
                        "$eq": [
                          "$quantity_before",
                          null
                        ]
                      },
                      {
                        "$eq": [
                          "$quantity_after",
                          null
                        ]
                      },
                      {
                        "$eq": [
                          "$price_snapshot",
                          null
                        ]
                      }
                    ]
                  }
                ]
              }
            },
            {
              "$expr": {
                "$or": [
                  {
                    "$not": [
                      {
                        "$in": [
                          "$event_type",
                          [
                            "ADD",
                            "REMOVE",
                            "QTY_CHANGE"
                          ]
                        ]
                      }
                    ]
                  },
                  {
                    "$ne": [
                      "$sku_id",
                      null
                    ]
                  }
                ]
              }
            }
          ]
        },
        "validationLevel": "strict",
        "validationAction": "error"
      },
      "indexes": [
        {
          "v": 2,
          "key": {
            "_id": 1
          },
          "name": "_id_"
        },
        {
          "v": 2,
          "key": {
            "cart_id": 1,
            "event_at": -1
          },
          "name": "idx_cart_events_cart_id_event_at"
        },
        {
          "v": 2,
          "key": {
            "user_id": 1,
            "event_at": -1
          },
          "name": "idx_cart_events_user_id_event_at"
        },
        {
          "v": 2,
          "key": {
            "event_type": 1,
            "event_at": -1
          },
          "name": "idx_cart_events_event_type_event_at"
        },
        {
          "v": 2,
          "key": {
            "product_id": 1,
            "event_at": -1
          },
          "name": "idx_cart_events_product_id_event_at"
        },
        {
          "v": 2,
          "key": {
            "user_id": 1,
            "operation_id": 1
          },
          "name": "uq_cart_events_user_id_operation_id",
          "unique": true
        },
        {
          "v": 2,
          "key": {
            "event_id": 1
          },
          "name": "uq_cart_events_event_id",
          "unique": true
        }
      ]
    },
    {
      "collection": "brands",
      "count": 0,
      "conforming_documents": 0,
      "options": {
        "validator": {
          "$jsonSchema": {
            "bsonType": "object",
            "required": [
              "_id",
              "schema_version",
              "brand_code",
              "name",
              "description",
              "status",
              "created_at",
              "updated_at"
            ],
            "properties": {
              "_id": {
                "bsonType": "objectId"
              },
              "schema_version": {
                "bsonType": "int",
                "enum": [
                  4
                ]
              },
              "brand_code": {
                "bsonType": "string",
                "maxLength": 100,
                "minLength": 1
              },
              "name": {
                "bsonType": "string",
                "maxLength": 100,
                "minLength": 1
              },
              "description": {
                "bsonType": [
                  "string",
                  "null"
                ],
                "maxLength": 1000
              },
              "status": {
                "enum": [
                  "active",
                  "inactive"
                ]
              },
              "created_at": {
                "bsonType": "date"
              },
              "updated_at": {
                "bsonType": "date"
              }
            },
            "additionalProperties": false
          }
        },
        "validationLevel": "strict",
        "validationAction": "error"
      },
      "indexes": [
        {
          "v": 2,
          "key": {
            "_id": 1
          },
          "name": "_id_"
        },
        {
          "v": 2,
          "key": {
            "brand_code": 1
          },
          "name": "uq_brands_brand_code",
          "unique": true
        },
        {
          "v": 2,
          "key": {
            "name": 1
          },
          "name": "idx_brands_name"
        }
      ]
    },
    {
      "collection": "product_skus",
      "count": 0,
      "conforming_documents": 0,
      "options": {
        "validator": {
          "$jsonSchema": {
            "bsonType": "object",
            "required": [
              "_id",
              "schema_version",
              "product_id",
              "sku_code",
              "variant_attributes",
              "price",
              "cost_price",
              "currency",
              "stock_quantity",
              "reserved_quantity",
              "available_quantity",
              "safety_stock",
              "stock_status",
              "barcode",
              "weight_grams",
              "status",
              "created_at",
              "updated_at"
            ],
            "properties": {
              "_id": {
                "bsonType": "objectId"
              },
              "schema_version": {
                "bsonType": "int",
                "enum": [
                  4
                ]
              },
              "product_id": {
                "bsonType": "objectId"
              },
              "sku_code": {
                "bsonType": "string",
                "maxLength": 100,
                "minLength": 1
              },
              "variant_attributes": {
                "bsonType": "object",
                "additionalProperties": {
                  "bsonType": "string",
                  "maxLength": 100
                }
              },
              "price": {
                "bsonType": "decimal",
                "minimum": {
                  "$numberDecimal": "0"
                }
              },
              "cost_price": {
                "bsonType": [
                  "decimal",
                  "null"
                ],
                "minimum": {
                  "$numberDecimal": "0"
                }
              },
              "currency": {
                "enum": [
                  "TWD"
                ]
              },
              "stock_quantity": {
                "bsonType": "int",
                "minimum": 0
              },
              "reserved_quantity": {
                "bsonType": "int",
                "minimum": 0
              },
              "available_quantity": {
                "bsonType": "int",
                "minimum": 0
              },
              "safety_stock": {
                "bsonType": "int",
                "minimum": 0
              },
              "stock_status": {
                "enum": [
                  "in_stock",
                  "low_stock",
                  "out_of_stock"
                ]
              },
              "barcode": {
                "bsonType": [
                  "string",
                  "null"
                ],
                "maxLength": 100
              },
              "weight_grams": {
                "bsonType": [
                  "int",
                  "null"
                ],
                "minimum": 0
              },
              "status": {
                "enum": [
                  "active",
                  "inactive"
                ]
              },
              "created_at": {
                "bsonType": "date"
              },
              "updated_at": {
                "bsonType": "date"
              }
            },
            "additionalProperties": false
          },
          "$and": [
            {
              "$expr": {
                "$eq": [
                  "$available_quantity",
                  {
                    "$subtract": [
                      "$stock_quantity",
                      "$reserved_quantity"
                    ]
                  }
                ]
              }
            },
            {
              "$expr": {
                "$and": [
                  {
                    "$lte": [
                      "$price",
                      {
                        "$numberDecimal": "9.999999999999999999999999999999999E+6144"
                      }
                    ]
                  },
                  {
                    "$eq": [
                      "$price",
                      {
                        "$round": [
                          "$price",
                          2
                        ]
                      }
                    ]
                  }
                ]
              }
            },
            {
              "$expr": {
                "$or": [
                  {
                    "$eq": [
                      "$cost_price",
                      null
                    ]
                  },
                  {
                    "$and": [
                      {
                        "$lte": [
                          "$cost_price",
                          {
                            "$numberDecimal": "9.999999999999999999999999999999999E+6144"
                          }
                        ]
                      },
                      {
                        "$eq": [
                          "$cost_price",
                          {
                            "$round": [
                              "$cost_price",
                              2
                            ]
                          }
                        ]
                      }
                    ]
                  }
                ]
              }
            }
          ]
        },
        "validationLevel": "strict",
        "validationAction": "error"
      },
      "indexes": [
        {
          "v": 2,
          "key": {
            "_id": 1
          },
          "name": "_id_"
        },
        {
          "v": 2,
          "key": {
            "sku_code": 1
          },
          "name": "uq_product_skus_sku_code",
          "unique": true
        },
        {
          "v": 2,
          "key": {
            "product_id": 1,
            "status": 1
          },
          "name": "idx_product_skus_product_id_status"
        }
      ]
    },
    {
      "collection": "product_reviews",
      "count": 0,
      "conforming_documents": 0,
      "options": {
        "validator": {
          "$jsonSchema": {
            "bsonType": "object",
            "required": [
              "_id",
              "schema_version",
              "product_id",
              "user_id",
              "order_id",
              "order_item_id",
              "rating",
              "review_title",
              "review_content",
              "verified_purchase",
              "status",
              "created_at",
              "updated_at"
            ],
            "properties": {
              "_id": {
                "bsonType": "objectId"
              },
              "schema_version": {
                "bsonType": "int",
                "enum": [
                  4
                ]
              },
              "product_id": {
                "bsonType": "objectId"
              },
              "user_id": {
                "bsonType": "objectId"
              },
              "order_id": {
                "bsonType": "objectId"
              },
              "order_item_id": {
                "bsonType": "objectId"
              },
              "rating": {
                "bsonType": "int",
                "minimum": 1,
                "maximum": 5
              },
              "review_title": {
                "bsonType": "string",
                "maxLength": 200
              },
              "review_content": {
                "bsonType": "string",
                "maxLength": 8000
              },
              "verified_purchase": {
                "enum": [
                  true
                ]
              },
              "status": {
                "enum": [
                  "pending",
                  "published",
                  "hidden",
                  "rejected"
                ]
              },
              "created_at": {
                "bsonType": "date"
              },
              "updated_at": {
                "bsonType": "date"
              }
            },
            "additionalProperties": false
          }
        },
        "validationLevel": "strict",
        "validationAction": "error"
      },
      "indexes": [
        {
          "v": 2,
          "key": {
            "_id": 1
          },
          "name": "_id_"
        },
        {
          "v": 2,
          "key": {
            "user_id": 1,
            "order_item_id": 1
          },
          "name": "uq_product_reviews_user_id_order_item_id",
          "unique": true
        },
        {
          "v": 2,
          "key": {
            "product_id": 1,
            "status": 1
          },
          "name": "idx_product_reviews_product_id_status"
        }
      ]
    },
    {
      "collection": "order_items",
      "count": 0,
      "conforming_documents": 0,
      "options": {
        "validator": {
          "$jsonSchema": {
            "bsonType": "object",
            "required": [
              "_id",
              "schema_version",
              "order_id",
              "user_id",
              "product_id",
              "sku_id",
              "product_code_snapshot",
              "product_name_snapshot",
              "major_category_id_snapshot",
              "minor_category_id_snapshot",
              "quantity",
              "unit_price",
              "line_total",
              "created_at"
            ],
            "properties": {
              "_id": {
                "bsonType": "objectId"
              },
              "schema_version": {
                "bsonType": "int",
                "enum": [
                  4
                ]
              },
              "order_id": {
                "bsonType": "objectId"
              },
              "user_id": {
                "bsonType": "objectId"
              },
              "product_id": {
                "bsonType": "objectId"
              },
              "sku_id": {
                "bsonType": "objectId"
              },
              "product_code_snapshot": {
                "bsonType": "string",
                "maxLength": 100,
                "minLength": 1
              },
              "product_name_snapshot": {
                "bsonType": "string",
                "maxLength": 200,
                "minLength": 1
              },
              "major_category_id_snapshot": {
                "bsonType": "objectId"
              },
              "minor_category_id_snapshot": {
                "bsonType": "objectId"
              },
              "quantity": {
                "bsonType": "int",
                "minimum": 1,
                "maximum": 99
              },
              "unit_price": {
                "bsonType": "decimal",
                "minimum": {
                  "$numberDecimal": "0"
                }
              },
              "line_total": {
                "bsonType": "decimal",
                "minimum": {
                  "$numberDecimal": "0"
                }
              },
              "created_at": {
                "bsonType": "date"
              }
            },
            "additionalProperties": false
          },
          "$and": [
            {
              "$expr": {
                "$eq": [
                  "$line_total",
                  {
                    "$multiply": [
                      "$unit_price",
                      "$quantity"
                    ]
                  }
                ]
              }
            },
            {
              "$expr": {
                "$and": [
                  {
                    "$lte": [
                      "$unit_price",
                      {
                        "$numberDecimal": "9.999999999999999999999999999999999E+6144"
                      }
                    ]
                  },
                  {
                    "$eq": [
                      "$unit_price",
                      {
                        "$round": [
                          "$unit_price",
                          2
                        ]
                      }
                    ]
                  }
                ]
              }
            }
          ]
        },
        "validationLevel": "strict",
        "validationAction": "error"
      },
      "indexes": [
        {
          "v": 2,
          "key": {
            "_id": 1
          },
          "name": "_id_"
        },
        {
          "v": 2,
          "key": {
            "product_id": 1,
            "created_at": -1
          },
          "name": "idx_order_items_product_id_created_at"
        },
        {
          "v": 2,
          "key": {
            "user_id": 1,
            "created_at": -1
          },
          "name": "idx_order_items_user_id_created_at"
        },
        {
          "v": 2,
          "key": {
            "order_id": 1
          },
          "name": "idx_order_items_order_id"
        },
        {
          "v": 2,
          "key": {
            "order_id": 1,
            "sku_id": 1
          },
          "name": "uq_order_items_order_id_sku_id",
          "unique": true
        }
      ]
    },
    {
      "collection": "behavior_events",
      "count": 0,
      "conforming_documents": 0,
      "options": {
        "validator": {
          "$jsonSchema": {
            "bsonType": "object",
            "required": [
              "_id",
              "schema_version",
              "event_id",
              "user_id",
              "anonymous_id",
              "session_id",
              "event_type",
              "product_id",
              "major_category_id",
              "minor_category_id",
              "quantity",
              "order_id",
              "cart_id",
              "search_query",
              "source",
              "recommendation_id",
              "event_at",
              "score_version",
              "processed_at",
              "metadata",
              "created_at"
            ],
            "properties": {
              "_id": {
                "bsonType": "objectId"
              },
              "schema_version": {
                "bsonType": "int",
                "enum": [
                  4
                ]
              },
              "event_id": {
                "bsonType": "string",
                "maxLength": 128,
                "minLength": 1
              },
              "user_id": {
                "bsonType": [
                  "objectId",
                  "null"
                ]
              },
              "anonymous_id": {
                "bsonType": [
                  "string",
                  "null"
                ],
                "maxLength": 128
              },
              "session_id": {
                "bsonType": "string",
                "maxLength": 128,
                "minLength": 1
              },
              "event_type": {
                "enum": [
                  "PURCHASE",
                  "ADD_TO_CART",
                  "SEARCH",
                  "PRODUCT_VIEW"
                ]
              },
              "product_id": {
                "bsonType": [
                  "objectId",
                  "null"
                ]
              },
              "major_category_id": {
                "bsonType": [
                  "objectId",
                  "null"
                ]
              },
              "minor_category_id": {
                "bsonType": [
                  "objectId",
                  "null"
                ]
              },
              "quantity": {
                "bsonType": "int",
                "minimum": 1
              },
              "order_id": {
                "bsonType": [
                  "objectId",
                  "null"
                ]
              },
              "cart_id": {
                "bsonType": [
                  "objectId",
                  "null"
                ]
              },
              "search_query": {
                "bsonType": [
                  "string",
                  "null"
                ],
                "maxLength": 200
              },
              "source": {
                "bsonType": "string",
                "maxLength": 100,
                "minLength": 1
              },
              "recommendation_id": {
                "bsonType": [
                  "string",
                  "null"
                ],
                "maxLength": 128
              },
              "event_at": {
                "bsonType": "date"
              },
              "score_version": {
                "bsonType": "int",
                "minimum": 1
              },
              "processed_at": {
                "bsonType": [
                  "date",
                  "null"
                ]
              },
              "metadata": {
                "bsonType": "object"
              },
              "created_at": {
                "bsonType": "date"
              }
            },
            "additionalProperties": false
          },
          "$and": [
            {
              "$expr": {
                "$or": [
                  {
                    "$ne": [
                      "$user_id",
                      null
                    ]
                  },
                  {
                    "$ne": [
                      "$anonymous_id",
                      null
                    ]
                  }
                ]
              }
            },
            {
              "$expr": {
                "$or": [
                  {
                    "$not": [
                      {
                        "$eq": [
                          "$event_type",
                          "PURCHASE"
                        ]
                      }
                    ]
                  },
                  {
                    "$and": [
                      {
                        "$ne": [
                          "$user_id",
                          null
                        ]
                      },
                      {
                        "$ne": [
                          "$order_id",
                          null
                        ]
                      },
                      {
                        "$ne": [
                          "$product_id",
                          null
                        ]
                      }
                    ]
                  }
                ]
              }
            },
            {
              "$expr": {
                "$or": [
                  {
                    "$not": [
                      {
                        "$in": [
                          "$event_type",
                          [
                            "ADD_TO_CART",
                            "PRODUCT_VIEW"
                          ]
                        ]
                      }
                    ]
                  },
                  {
                    "$ne": [
                      "$product_id",
                      null
                    ]
                  }
                ]
              }
            },
            {
              "$expr": {
                "$or": [
                  {
                    "$not": [
                      {
                        "$eq": [
                          "$event_type",
                          "SEARCH"
                        ]
                      }
                    ]
                  },
                  {
                    "$and": [
                      {
                        "$ne": [
                          "$search_query",
                          null
                        ]
                      },
                      {
                        "$ne": [
                          "$search_query",
                          ""
                        ]
                      }
                    ]
                  }
                ]
              }
            },
            {
              "$expr": {
                "$lte": [
                  {
                    "$bsonSize": "$metadata"
                  },
                  2048
                ]
              }
            }
          ]
        },
        "validationLevel": "strict",
        "validationAction": "error"
      },
      "indexes": [
        {
          "v": 2,
          "key": {
            "_id": 1
          },
          "name": "_id_"
        },
        {
          "v": 2,
          "key": {
            "event_id": 1
          },
          "name": "uq_behavior_events_event_id",
          "unique": true
        },
        {
          "v": 2,
          "key": {
            "user_id": 1,
            "event_at": -1
          },
          "name": "idx_behavior_events_user_id_event_at"
        },
        {
          "v": 2,
          "key": {
            "user_id": 1,
            "event_type": 1,
            "event_at": -1
          },
          "name": "idx_behavior_events_user_id_event_type_event_at"
        },
        {
          "v": 2,
          "key": {
            "product_id": 1,
            "event_at": -1
          },
          "name": "idx_behavior_events_product_id_event_at"
        },
        {
          "v": 2,
          "key": {
            "processed_at": 1,
            "event_at": 1
          },
          "name": "idx_behavior_events_processed_at_event_at"
        }
      ]
    },
    {
      "collection": "user_preference_scores",
      "count": 0,
      "conforming_documents": 0,
      "options": {
        "validator": {
          "$jsonSchema": {
            "bsonType": "object",
            "required": [
              "_id",
              "schema_version",
              "user_id",
              "score_version",
              "major_categories",
              "minor_categories",
              "products",
              "cross_category_scores",
              "last_processed_event_at",
              "updated_at"
            ],
            "properties": {
              "_id": {
                "bsonType": "objectId"
              },
              "schema_version": {
                "bsonType": "int",
                "enum": [
                  4
                ]
              },
              "user_id": {
                "bsonType": "objectId"
              },
              "score_version": {
                "bsonType": "int",
                "minimum": 1
              },
              "major_categories": {
                "bsonType": "object",
                "additionalProperties": {
                  "bsonType": "object",
                  "required": [
                    "raw_score",
                    "score",
                    "last_event_at"
                  ],
                  "properties": {
                    "raw_score": {
                      "bsonType": "double",
                      "minimum": 0,
                      "maximum": 1.7976931348623157e+308
                    },
                    "score": {
                      "bsonType": "double",
                      "minimum": 0,
                      "maximum": 70
                    },
                    "last_event_at": {
                      "bsonType": "date"
                    }
                  },
                  "additionalProperties": false
                }
              },
              "minor_categories": {
                "bsonType": "object",
                "additionalProperties": {
                  "bsonType": "object",
                  "required": [
                    "raw_score",
                    "score",
                    "last_event_at"
                  ],
                  "properties": {
                    "raw_score": {
                      "bsonType": "double",
                      "minimum": 0,
                      "maximum": 1.7976931348623157e+308
                    },
                    "score": {
                      "bsonType": "double",
                      "minimum": 0,
                      "maximum": 30
                    },
                    "last_event_at": {
                      "bsonType": "date"
                    }
                  },
                  "additionalProperties": false
                }
              },
              "products": {
                "bsonType": "object",
                "additionalProperties": {
                  "bsonType": "object",
                  "required": [
                    "raw_score",
                    "score",
                    "last_event_at"
                  ],
                  "properties": {
                    "raw_score": {
                      "bsonType": "double",
                      "minimum": 0,
                      "maximum": 1.7976931348623157e+308
                    },
                    "score": {
                      "bsonType": "double",
                      "minimum": 0,
                      "maximum": 1.7976931348623157e+308
                    },
                    "last_event_at": {
                      "bsonType": "date"
                    }
                  },
                  "additionalProperties": false
                }
              },
              "cross_category_scores": {
                "bsonType": "object",
                "additionalProperties": {
                  "bsonType": "object",
                  "required": [
                    "raw_score",
                    "score",
                    "last_event_at"
                  ],
                  "properties": {
                    "raw_score": {
                      "bsonType": "double",
                      "minimum": 0,
                      "maximum": 1.7976931348623157e+308
                    },
                    "score": {
                      "bsonType": "double",
                      "minimum": 0,
                      "maximum": 1.7976931348623157e+308
                    },
                    "last_event_at": {
                      "bsonType": "date"
                    }
                  },
                  "additionalProperties": false
                }
              },
              "last_processed_event_at": {
                "bsonType": [
                  "date",
                  "null"
                ]
              },
              "updated_at": {
                "bsonType": "date"
              }
            },
            "additionalProperties": false
          }
        },
        "validationLevel": "strict",
        "validationAction": "error"
      },
      "indexes": [
        {
          "v": 2,
          "key": {
            "_id": 1
          },
          "name": "_id_"
        },
        {
          "v": 2,
          "key": {
            "user_id": 1
          },
          "name": "uq_user_preference_scores_user_id",
          "unique": true
        }
      ]
    },
    {
      "collection": "product_repurchase_stats",
      "count": 0,
      "conforming_documents": 0,
      "options": {
        "validator": {
          "$jsonSchema": {
            "bsonType": "object",
            "required": [
              "_id",
              "schema_version",
              "product_id",
              "major_category_id",
              "minor_category_id",
              "period_type",
              "period_start",
              "period_end",
              "unique_buyer_count",
              "repeat_customer_count",
              "order_count",
              "repeat_purchase_rate",
              "avg_purchase_frequency",
              "median_repurchase_interval_days",
              "p25_repurchase_interval_days",
              "p75_repurchase_interval_days",
              "sample_size_status",
              "calculated_at"
            ],
            "properties": {
              "_id": {
                "bsonType": "objectId"
              },
              "schema_version": {
                "bsonType": "int",
                "enum": [
                  4
                ]
              },
              "product_id": {
                "bsonType": "objectId"
              },
              "major_category_id": {
                "bsonType": "objectId"
              },
              "minor_category_id": {
                "bsonType": "objectId"
              },
              "period_type": {
                "enum": [
                  "12m"
                ]
              },
              "period_start": {
                "bsonType": "date"
              },
              "period_end": {
                "bsonType": "date"
              },
              "unique_buyer_count": {
                "bsonType": "int",
                "minimum": 0
              },
              "repeat_customer_count": {
                "bsonType": "int",
                "minimum": 0
              },
              "order_count": {
                "bsonType": "int",
                "minimum": 0
              },
              "repeat_purchase_rate": {
                "bsonType": [
                  "double",
                  "null"
                ],
                "minimum": 0,
                "maximum": 1
              },
              "avg_purchase_frequency": {
                "bsonType": [
                  "double",
                  "null"
                ],
                "minimum": 0,
                "maximum": 1.7976931348623157e+308
              },
              "median_repurchase_interval_days": {
                "bsonType": [
                  "double",
                  "null"
                ],
                "minimum": 0,
                "maximum": 1.7976931348623157e+308
              },
              "p25_repurchase_interval_days": {
                "bsonType": [
                  "double",
                  "null"
                ],
                "minimum": 0,
                "maximum": 1.7976931348623157e+308
              },
              "p75_repurchase_interval_days": {
                "bsonType": [
                  "double",
                  "null"
                ],
                "minimum": 0,
                "maximum": 1.7976931348623157e+308
              },
              "sample_size_status": {
                "enum": [
                  "insufficient",
                  "adequate"
                ]
              },
              "calculated_at": {
                "bsonType": "date"
              }
            },
            "additionalProperties": false
          },
          "$and": [
            {
              "$expr": {
                "$lt": [
                  "$period_start",
                  "$period_end"
                ]
              }
            },
            {
              "$expr": {
                "$lte": [
                  "$repeat_customer_count",
                  "$unique_buyer_count"
                ]
              }
            },
            {
              "$expr": {
                "$cond": [
                  {
                    "$eq": [
                      "$unique_buyer_count",
                      0
                    ]
                  },
                  {
                    "$and": [
                      {
                        "$eq": [
                          "$repeat_purchase_rate",
                          null
                        ]
                      },
                      {
                        "$eq": [
                          "$avg_purchase_frequency",
                          null
                        ]
                      }
                    ]
                  },
                  {
                    "$and": [
                      {
                        "$eq": [
                          "$repeat_purchase_rate",
                          {
                            "$divide": [
                              "$repeat_customer_count",
                              "$unique_buyer_count"
                            ]
                          }
                        ]
                      },
                      {
                        "$eq": [
                          "$avg_purchase_frequency",
                          {
                            "$divide": [
                              "$order_count",
                              "$unique_buyer_count"
                            ]
                          }
                        ]
                      }
                    ]
                  }
                ]
              }
            }
          ]
        },
        "validationLevel": "strict",
        "validationAction": "error"
      },
      "indexes": [
        {
          "v": 2,
          "key": {
            "_id": 1
          },
          "name": "_id_"
        },
        {
          "v": 2,
          "key": {
            "product_id": 1,
            "period_type": 1,
            "period_start": 1,
            "period_end": 1
          },
          "name": "uq_product_repurchase_stats_product_id_period_type_period_start_period_end",
          "unique": true
        }
      ]
    },
    {
      "collection": "cross_category_rules",
      "count": 0,
      "conforming_documents": 0,
      "options": {
        "validator": {
          "$jsonSchema": {
            "bsonType": "object",
            "required": [
              "_id",
              "schema_version",
              "antecedent",
              "consequent",
              "window_days",
              "support",
              "confidence",
              "lift",
              "co_purchase_count",
              "antecedent_customer_count",
              "rule_score",
              "minimum_sample_size",
              "source",
              "status",
              "calculated_at"
            ],
            "properties": {
              "_id": {
                "bsonType": "objectId"
              },
              "schema_version": {
                "bsonType": "int",
                "enum": [
                  4
                ]
              },
              "antecedent": {
                "bsonType": "object",
                "required": [
                  "major_category_id",
                  "minor_category_id"
                ],
                "properties": {
                  "major_category_id": {
                    "bsonType": "objectId"
                  },
                  "minor_category_id": {
                    "bsonType": "objectId"
                  }
                },
                "additionalProperties": false
              },
              "consequent": {
                "bsonType": "object",
                "required": [
                  "major_category_id",
                  "minor_category_id"
                ],
                "properties": {
                  "major_category_id": {
                    "bsonType": "objectId"
                  },
                  "minor_category_id": {
                    "bsonType": "objectId"
                  }
                },
                "additionalProperties": false
              },
              "window_days": {
                "bsonType": "int",
                "minimum": 1
              },
              "support": {
                "bsonType": "double",
                "minimum": 0,
                "maximum": 1
              },
              "confidence": {
                "bsonType": "double",
                "minimum": 0,
                "maximum": 1
              },
              "lift": {
                "bsonType": "double",
                "minimum": 0,
                "maximum": 1.7976931348623157e+308
              },
              "co_purchase_count": {
                "bsonType": "int",
                "minimum": 0
              },
              "antecedent_customer_count": {
                "bsonType": "int",
                "minimum": 0
              },
              "rule_score": {
                "bsonType": "double",
                "minimum": 0,
                "maximum": 1.7976931348623157e+308
              },
              "minimum_sample_size": {
                "bsonType": "int",
                "minimum": 1
              },
              "source": {
                "enum": [
                  "historical_transactions"
                ]
              },
              "status": {
                "enum": [
                  "active",
                  "inactive"
                ]
              },
              "calculated_at": {
                "bsonType": "date"
              }
            },
            "additionalProperties": false
          },
          "$and": [
            {
              "$expr": {
                "$lte": [
                  "$co_purchase_count",
                  "$antecedent_customer_count"
                ]
              }
            }
          ]
        },
        "validationLevel": "strict",
        "validationAction": "error"
      },
      "indexes": [
        {
          "v": 2,
          "key": {
            "_id": 1
          },
          "name": "_id_"
        },
        {
          "v": 2,
          "key": {
            "antecedent.major_category_id": 1,
            "status": 1
          },
          "name": "idx_cross_category_rules_antecedent_major_category_id_status"
        },
        {
          "v": 2,
          "key": {
            "antecedent.minor_category_id": 1,
            "confidence": -1,
            "lift": -1
          },
          "name": "idx_cross_category_rules_antecedent_minor_category_id_confidence_lift"
        }
      ]
    },
    {
      "collection": "product_purchase_sequences",
      "count": 0,
      "conforming_documents": 0,
      "options": {
        "validator": {
          "$jsonSchema": {
            "bsonType": "object",
            "required": [
              "_id",
              "schema_version",
              "user_id",
              "first_product_id",
              "next_product_id",
              "first_order_id",
              "next_order_id",
              "days_between",
              "window_days",
              "first_major_category_id",
              "next_major_category_id",
              "created_at"
            ],
            "properties": {
              "_id": {
                "bsonType": "objectId"
              },
              "schema_version": {
                "bsonType": "int",
                "enum": [
                  4
                ]
              },
              "user_id": {
                "bsonType": "objectId"
              },
              "first_product_id": {
                "bsonType": "objectId"
              },
              "next_product_id": {
                "bsonType": "objectId"
              },
              "first_order_id": {
                "bsonType": "objectId"
              },
              "next_order_id": {
                "bsonType": "objectId"
              },
              "days_between": {
                "bsonType": "int",
                "minimum": 0
              },
              "window_days": {
                "bsonType": "int",
                "minimum": 1
              },
              "first_major_category_id": {
                "bsonType": "objectId"
              },
              "next_major_category_id": {
                "bsonType": "objectId"
              },
              "created_at": {
                "bsonType": "date"
              }
            },
            "additionalProperties": false
          },
          "$and": [
            {
              "$expr": {
                "$lte": [
                  "$days_between",
                  "$window_days"
                ]
              }
            }
          ]
        },
        "validationLevel": "strict",
        "validationAction": "error"
      },
      "indexes": [
        {
          "v": 2,
          "key": {
            "_id": 1
          },
          "name": "_id_"
        },
        {
          "v": 2,
          "key": {
            "user_id": 1,
            "first_order_id": 1,
            "next_order_id": 1,
            "first_product_id": 1,
            "next_product_id": 1
          },
          "name": "uq_product_purchase_sequences_user_id_first_order_id_next_order_id_first_product_id_next_product_id",
          "unique": true
        }
      ]
    },
    {
      "collection": "recommendation_pools",
      "count": 0,
      "conforming_documents": 0,
      "options": {
        "validator": {
          "$jsonSchema": {
            "bsonType": "object",
            "required": [
              "_id",
              "schema_version",
              "pool_type",
              "major_category_id",
              "product_ids",
              "filters",
              "generated_at",
              "expires_at"
            ],
            "properties": {
              "_id": {
                "bsonType": "objectId"
              },
              "schema_version": {
                "bsonType": "int",
                "enum": [
                  4
                ]
              },
              "pool_type": {
                "enum": [
                  "FIRST_MEMBER"
                ]
              },
              "major_category_id": {
                "bsonType": "objectId"
              },
              "product_ids": {
                "bsonType": "array",
                "items": {
                  "bsonType": "objectId"
                },
                "minItems": 0,
                "uniqueItems": true
              },
              "filters": {
                "bsonType": "object",
                "required": [
                  "rating_status",
                  "average_rating_display_gte",
                  "status",
                  "is_ai_recommendable"
                ],
                "properties": {
                  "rating_status": {
                    "enum": [
                      "ACTUAL"
                    ]
                  },
                  "average_rating_display_gte": {
                    "bsonType": "double",
                    "minimum": 4.5,
                    "maximum": 5
                  },
                  "status": {
                    "enum": [
                      "active"
                    ]
                  },
                  "is_ai_recommendable": {
                    "enum": [
                      true
                    ]
                  }
                },
                "additionalProperties": false
              },
              "generated_at": {
                "bsonType": "date"
              },
              "expires_at": {
                "bsonType": "date"
              }
            },
            "additionalProperties": false
          },
          "$and": [
            {
              "$expr": {
                "$lt": [
                  "$generated_at",
                  "$expires_at"
                ]
              }
            }
          ]
        },
        "validationLevel": "strict",
        "validationAction": "error"
      },
      "indexes": [
        {
          "v": 2,
          "key": {
            "_id": 1
          },
          "name": "_id_"
        },
        {
          "v": 2,
          "key": {
            "pool_type": 1,
            "major_category_id": 1
          },
          "name": "uq_recommendation_pools_pool_type_major_category_id",
          "unique": true
        }
      ]
    },
    {
      "collection": "first_member_recommendations",
      "count": 0,
      "conforming_documents": 0,
      "options": {
        "validator": {
          "$jsonSchema": {
            "bsonType": "object",
            "required": [
              "_id",
              "schema_version",
              "user_id",
              "recommendation_session_id",
              "recommendation_type",
              "items",
              "rule_version",
              "random_seed",
              "created_at"
            ],
            "properties": {
              "_id": {
                "bsonType": "objectId"
              },
              "schema_version": {
                "bsonType": "int",
                "enum": [
                  4
                ]
              },
              "user_id": {
                "bsonType": "objectId"
              },
              "recommendation_session_id": {
                "bsonType": "string",
                "maxLength": 128,
                "minLength": 1
              },
              "recommendation_type": {
                "enum": [
                  "FIRST_MEMBER"
                ]
              },
              "items": {
                "bsonType": "array",
                "items": {
                  "bsonType": "object",
                  "required": [
                    "major_category_id",
                    "product_id",
                    "average_rating_display",
                    "rating_count",
                    "position"
                  ],
                  "properties": {
                    "major_category_id": {
                      "bsonType": "objectId"
                    },
                    "product_id": {
                      "bsonType": "objectId"
                    },
                    "average_rating_display": {
                      "bsonType": "double",
                      "minimum": 4.5,
                      "maximum": 5
                    },
                    "rating_count": {
                      "bsonType": "int",
                      "minimum": 1
                    },
                    "position": {
                      "bsonType": "int",
                      "minimum": 1
                    }
                  },
                  "additionalProperties": false
                },
                "minItems": 0,
                "uniqueItems": false
              },
              "rule_version": {
                "bsonType": "int",
                "minimum": 1
              },
              "random_seed": {
                "bsonType": "string",
                "maxLength": 128,
                "minLength": 1
              },
              "created_at": {
                "bsonType": "date"
              }
            },
            "additionalProperties": false
          },
          "$and": [
            {
              "$expr": {
                "$eq": [
                  {
                    "$size": "$items"
                  },
                  {
                    "$size": {
                      "$setUnion": [
                        "$items.major_category_id",
                        []
                      ]
                    }
                  }
                ]
              }
            },
            {
              "$expr": {
                "$eq": [
                  {
                    "$size": "$items"
                  },
                  {
                    "$size": {
                      "$setUnion": [
                        "$items.product_id",
                        []
                      ]
                    }
                  }
                ]
              }
            },
            {
              "$expr": {
                "$eq": [
                  "$items.position",
                  {
                    "$range": [
                      1,
                      {
                        "$add": [
                          {
                            "$size": "$items"
                          },
                          1
                        ]
                      }
                    ]
                  }
                ]
              }
            }
          ]
        },
        "validationLevel": "strict",
        "validationAction": "error"
      },
      "indexes": [
        {
          "v": 2,
          "key": {
            "_id": 1
          },
          "name": "_id_"
        },
        {
          "v": 2,
          "key": {
            "user_id": 1
          },
          "name": "uq_first_member_recommendations_user_id",
          "unique": true
        }
      ]
    },
    {
      "collection": "recommendation_logs",
      "count": 0,
      "conforming_documents": 0,
      "options": {
        "validator": {
          "$jsonSchema": {
            "bsonType": "object",
            "required": [
              "_id",
              "schema_version",
              "user_id",
              "recommendation_id",
              "recommendation_type",
              "algorithm_version",
              "items",
              "shown_at",
              "clicked_product_ids",
              "added_to_cart_product_ids",
              "purchased_product_ids",
              "created_at"
            ],
            "properties": {
              "_id": {
                "bsonType": "objectId"
              },
              "schema_version": {
                "bsonType": "int",
                "enum": [
                  4
                ]
              },
              "user_id": {
                "bsonType": "objectId"
              },
              "recommendation_id": {
                "bsonType": "string",
                "maxLength": 128,
                "minLength": 1
              },
              "recommendation_type": {
                "enum": [
                  "PERSONALIZED",
                  "CROSS_CATEGORY",
                  "FIRST_MEMBER"
                ]
              },
              "algorithm_version": {
                "bsonType": "string",
                "maxLength": 100,
                "minLength": 1
              },
              "items": {
                "bsonType": "array",
                "items": {
                  "bsonType": "object",
                  "required": [
                    "product_id",
                    "position",
                    "score",
                    "reason_code"
                  ],
                  "properties": {
                    "product_id": {
                      "bsonType": "objectId"
                    },
                    "position": {
                      "bsonType": "int",
                      "minimum": 1
                    },
                    "score": {
                      "bsonType": "double",
                      "minimum": 0,
                      "maximum": 1.7976931348623157e+308
                    },
                    "reason_code": {
                      "bsonType": "string",
                      "maxLength": 100,
                      "minLength": 1
                    }
                  },
                  "additionalProperties": false
                },
                "minItems": 0,
                "uniqueItems": false
              },
              "shown_at": {
                "bsonType": "date"
              },
              "clicked_product_ids": {
                "bsonType": "array",
                "items": {
                  "bsonType": "objectId"
                },
                "minItems": 0,
                "uniqueItems": true
              },
              "added_to_cart_product_ids": {
                "bsonType": "array",
                "items": {
                  "bsonType": "objectId"
                },
                "minItems": 0,
                "uniqueItems": true
              },
              "purchased_product_ids": {
                "bsonType": "array",
                "items": {
                  "bsonType": "objectId"
                },
                "minItems": 0,
                "uniqueItems": true
              },
              "created_at": {
                "bsonType": "date"
              }
            },
            "additionalProperties": false
          },
          "$and": [
            {
              "$expr": {
                "$eq": [
                  {
                    "$size": "$items"
                  },
                  {
                    "$size": {
                      "$setUnion": [
                        "$items.product_id",
                        []
                      ]
                    }
                  }
                ]
              }
            },
            {
              "$expr": {
                "$eq": [
                  "$items.position",
                  {
                    "$range": [
                      1,
                      {
                        "$add": [
                          {
                            "$size": "$items"
                          },
                          1
                        ]
                      }
                    ]
                  }
                ]
              }
            },
            {
              "$expr": {
                "$or": [
                  {
                    "$not": [
                      {
                        "$eq": [
                          "$recommendation_type",
                          "PERSONALIZED"
                        ]
                      }
                    ]
                  },
                  {
                    "$lte": [
                      {
                        "$size": "$items"
                      },
                      6
                    ]
                  }
                ]
              }
            },
            {
              "$expr": {
                "$or": [
                  {
                    "$not": [
                      {
                        "$eq": [
                          "$recommendation_type",
                          "CROSS_CATEGORY"
                        ]
                      }
                    ]
                  },
                  {
                    "$lte": [
                      {
                        "$size": "$items"
                      },
                      4
                    ]
                  }
                ]
              }
            },
            {
              "$expr": {
                "$setIsSubset": [
                  "$clicked_product_ids",
                  "$items.product_id"
                ]
              }
            },
            {
              "$expr": {
                "$setIsSubset": [
                  "$added_to_cart_product_ids",
                  "$items.product_id"
                ]
              }
            },
            {
              "$expr": {
                "$setIsSubset": [
                  "$purchased_product_ids",
                  "$items.product_id"
                ]
              }
            }
          ]
        },
        "validationLevel": "strict",
        "validationAction": "error"
      },
      "indexes": [
        {
          "v": 2,
          "key": {
            "_id": 1
          },
          "name": "_id_"
        },
        {
          "v": 2,
          "key": {
            "recommendation_id": 1
          },
          "name": "uq_recommendation_logs_recommendation_id",
          "unique": true
        },
        {
          "v": 2,
          "key": {
            "user_id": 1,
            "shown_at": -1
          },
          "name": "idx_recommendation_logs_user_id_shown_at"
        }
      ]
    },
    {
      "collection": "system_configs",
      "count": 1,
      "conforming_documents": 1,
      "options": {
        "validator": {
          "$jsonSchema": {
            "bsonType": "object",
            "required": [
              "_id",
              "schema_version",
              "config_key",
              "version",
              "settings",
              "status",
              "created_at",
              "updated_at"
            ],
            "properties": {
              "_id": {
                "bsonType": "objectId"
              },
              "schema_version": {
                "bsonType": "int",
                "enum": [
                  4
                ]
              },
              "config_key": {
                "enum": [
                  "recommendation_policy"
                ]
              },
              "version": {
                "bsonType": "int",
                "minimum": 1
              },
              "settings": {
                "bsonType": "object",
                "required": [
                  "weights",
                  "half_life_days",
                  "major_score_cap",
                  "minor_score_cap",
                  "personalized_count",
                  "cross_category_count",
                  "first_member_min_rating",
                  "default_product_rating",
                  "cross_min_customers",
                  "cross_min_co_purchases",
                  "cross_min_confidence",
                  "cross_min_lift"
                ],
                "properties": {
                  "weights": {
                    "bsonType": "object",
                    "required": [
                      "PURCHASE",
                      "ADD_TO_CART",
                      "SEARCH",
                      "PRODUCT_VIEW"
                    ],
                    "properties": {
                      "PURCHASE": {
                        "bsonType": "int",
                        "minimum": 0
                      },
                      "ADD_TO_CART": {
                        "bsonType": "int",
                        "minimum": 0
                      },
                      "SEARCH": {
                        "bsonType": "int",
                        "minimum": 0
                      },
                      "PRODUCT_VIEW": {
                        "bsonType": "int",
                        "minimum": 0
                      }
                    },
                    "additionalProperties": false
                  },
                  "half_life_days": {
                    "bsonType": "object",
                    "required": [
                      "PURCHASE",
                      "ADD_TO_CART",
                      "SEARCH",
                      "PRODUCT_VIEW"
                    ],
                    "properties": {
                      "PURCHASE": {
                        "bsonType": "int",
                        "minimum": 1
                      },
                      "ADD_TO_CART": {
                        "bsonType": "int",
                        "minimum": 1
                      },
                      "SEARCH": {
                        "bsonType": "int",
                        "minimum": 1
                      },
                      "PRODUCT_VIEW": {
                        "bsonType": "int",
                        "minimum": 1
                      }
                    },
                    "additionalProperties": false
                  },
                  "major_score_cap": {
                    "bsonType": "int",
                    "enum": [
                      70
                    ]
                  },
                  "minor_score_cap": {
                    "bsonType": "int",
                    "enum": [
                      30
                    ]
                  },
                  "personalized_count": {
                    "bsonType": "int",
                    "enum": [
                      6
                    ]
                  },
                  "cross_category_count": {
                    "bsonType": "int",
                    "enum": [
                      4
                    ]
                  },
                  "first_member_min_rating": {
                    "bsonType": "double",
                    "minimum": 4.5,
                    "maximum": 5
                  },
                  "default_product_rating": {
                    "bsonType": "double",
                    "minimum": 4,
                    "maximum": 4
                  },
                  "cross_min_customers": {
                    "bsonType": "int",
                    "minimum": 1
                  },
                  "cross_min_co_purchases": {
                    "bsonType": "int",
                    "minimum": 1
                  },
                  "cross_min_confidence": {
                    "bsonType": "double",
                    "minimum": 0,
                    "maximum": 1
                  },
                  "cross_min_lift": {
                    "bsonType": "double",
                    "minimum": 1,
                    "maximum": 1.7976931348623157e+308
                  }
                },
                "additionalProperties": false
              },
              "status": {
                "enum": [
                  "active",
                  "inactive"
                ]
              },
              "created_at": {
                "bsonType": "date"
              },
              "updated_at": {
                "bsonType": "date"
              }
            },
            "additionalProperties": false
          }
        },
        "validationLevel": "strict",
        "validationAction": "error"
      },
      "indexes": [
        {
          "v": 2,
          "key": {
            "_id": 1
          },
          "name": "_id_"
        },
        {
          "v": 2,
          "key": {
            "config_key": 1
          },
          "name": "uq_system_configs_config_key",
          "unique": true
        }
      ]
    }
  ],
  "system_configs": [
    {
      "_id": {
        "$oid": "6aad5f98bb50ad73772cfe86"
      },
      "schema_version": 4,
      "config_key": "recommendation_policy",
      "version": 1,
      "status": "active",
      "created_at": {
        "$date": "2026-09-18T15:58:16.708Z"
      },
      "updated_at": {
        "$date": "2026-09-18T15:58:16.708Z"
      },
      "settings": {
        "weights": {
          "PURCHASE": 4,
          "ADD_TO_CART": 3,
          "SEARCH": 2,
          "PRODUCT_VIEW": 1
        },
        "half_life_days": {
          "PURCHASE": 365,
          "ADD_TO_CART": 180,
          "SEARCH": 90,
          "PRODUCT_VIEW": 30
        },
        "major_score_cap": 70,
        "minor_score_cap": 30,
        "personalized_count": 6,
        "cross_category_count": 4,
        "first_member_min_rating": 4.5,
        "default_product_rating": 4.0,
        "cross_min_customers": 500,
        "cross_min_co_purchases": 50,
        "cross_min_confidence": 0.05,
        "cross_min_lift": 1.2
      }
    }
  ]
}
```
