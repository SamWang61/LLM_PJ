# Schema 完整性更新前結構

```json
{
  "checked_at": {
    "$date": "2026-09-18T11:37:23.706Z"
  },
  "collections": [
    {
      "collection": "users",
      "count": 0,
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
        }
      ]
    },
    {
      "collection": "categories",
      "count": 0,
      "options": {
        "validator": {
          "$jsonSchema": {
            "bsonType": "object",
            "required": [
              "_id",
              "schema_version",
              "name",
              "slug",
              "description",
              "sort_order",
              "is_active",
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
              "name": {
                "bsonType": "string",
                "maxLength": 100,
                "minLength": 1
              },
              "slug": {
                "bsonType": "string",
                "pattern": "^[a-z0-9-]+$",
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
              "sort_order": {
                "bsonType": "int",
                "minimum": 0
              },
              "is_active": {
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
            "name": 1
          },
          "name": "uq_categories_name",
          "unique": true
        },
        {
          "v": 2,
          "key": {
            "slug": 1
          },
          "name": "uq_categories_slug",
          "unique": true
        }
      ]
    },
    {
      "collection": "products",
      "count": 0,
      "options": {
        "validator": {
          "$jsonSchema": {
            "bsonType": "object",
            "required": [
              "_id",
              "schema_version",
              "category_id",
              "name",
              "description",
              "sku",
              "brand",
              "size",
              "color",
              "price",
              "sale_price",
              "currency",
              "stock_quantity",
              "safety_stock",
              "tags",
              "image_urls",
              "is_active",
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
              "category_id": {
                "bsonType": "objectId"
              },
              "name": {
                "bsonType": "string",
                "maxLength": 200,
                "minLength": 1
              },
              "description": {
                "bsonType": "string",
                "maxLength": 5000,
                "minLength": 1
              },
              "sku": {
                "bsonType": "string",
                "pattern": "^[^a-z\\s]+$",
                "maxLength": 64,
                "minLength": 1
              },
              "brand": {
                "bsonType": [
                  "string",
                  "null"
                ],
                "maxLength": 100
              },
              "size": {
                "bsonType": [
                  "string",
                  "null"
                ],
                "maxLength": 100
              },
              "color": {
                "bsonType": [
                  "string",
                  "null"
                ],
                "maxLength": 100
              },
              "price": {
                "bsonType": "decimal",
                "minimum": {
                  "$numberDecimal": "0"
                }
              },
              "sale_price": {
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
              "safety_stock": {
                "bsonType": "int",
                "minimum": 0
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
              "image_urls": {
                "bsonType": "array",
                "items": {
                  "bsonType": "string",
                  "pattern": "^(https://|/(?!/))"
                },
                "minItems": 0,
                "maxItems": 10,
                "uniqueItems": false
              },
              "is_active": {
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
                "$and": [
                  {
                    "$lte": [
                      "$price",
                      {
                        "$numberDecimal": "1.000000000000000000000000000000000E+6144"
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
                      "$sale_price",
                      null
                    ]
                  },
                  {
                    "$and": [
                      {
                        "$lte": [
                          "$sale_price",
                          {
                            "$numberDecimal": "1.000000000000000000000000000000000E+6144"
                          }
                        ]
                      },
                      {
                        "$eq": [
                          "$sale_price",
                          {
                            "$round": [
                              "$sale_price",
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
                      "$sale_price",
                      null
                    ]
                  },
                  {
                    "$lte": [
                      "$sale_price",
                      "$price"
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
            "sku": 1
          },
          "name": "uq_products_sku",
          "unique": true
        },
        {
          "v": 2,
          "key": {
            "_fts": "text",
            "_ftsx": 1
          },
          "name": "idx_products_name_description_text",
          "weights": {
            "description": 1,
            "name": 1
          },
          "default_language": "none",
          "language_override": "language",
          "textIndexVersion": 3
        },
        {
          "v": 2,
          "key": {
            "category_id": 1,
            "is_active": 1
          },
          "name": "idx_products_category_id_is_active"
        }
      ]
    },
    {
      "collection": "carts",
      "count": 0,
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
                  3
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
                    "updated_at"
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
                                "$numberDecimal": "1.000000000000000000000000000000000E+6144"
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
      "options": {
        "validator": {
          "$jsonSchema": {
            "bsonType": "object",
            "required": [
              "_id",
              "schema_version",
              "order_number",
              "user_id",
              "checkout_id",
              "request_hash",
              "status",
              "payment_status",
              "is_demo",
              "currency",
              "items",
              "subtotal_amount",
              "discount_amount",
              "shipping_fee",
              "total_amount",
              "shipping_address",
              "paid_at",
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
              "order_number": {
                "bsonType": "string",
                "minLength": 1
              },
              "user_id": {
                "bsonType": "objectId"
              },
              "checkout_id": {
                "bsonType": "string",
                "minLength": 1
              },
              "request_hash": {
                "bsonType": "string",
                "pattern": "^[a-f0-9]{64}$",
                "maxLength": 64,
                "minLength": 64
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
              "is_demo": {
                "bsonType": "bool"
              },
              "currency": {
                "enum": [
                  "TWD"
                ]
              },
              "items": {
                "bsonType": "array",
                "items": {
                  "bsonType": "object",
                  "required": [
                    "product_id",
                    "product_name",
                    "sku",
                    "size",
                    "color",
                    "unit_price",
                    "quantity",
                    "subtotal_amount"
                  ],
                  "properties": {
                    "product_id": {
                      "bsonType": "objectId"
                    },
                    "product_name": {
                      "bsonType": "string",
                      "maxLength": 200,
                      "minLength": 1
                    },
                    "sku": {
                      "bsonType": "string",
                      "maxLength": 64,
                      "minLength": 1
                    },
                    "size": {
                      "bsonType": [
                        "string",
                        "null"
                      ],
                      "maxLength": 100
                    },
                    "color": {
                      "bsonType": [
                        "string",
                        "null"
                      ],
                      "maxLength": 100
                    },
                    "unit_price": {
                      "bsonType": "decimal",
                      "minimum": {
                        "$numberDecimal": "0"
                      }
                    },
                    "quantity": {
                      "bsonType": "int",
                      "minimum": 1,
                      "maximum": 99
                    },
                    "subtotal_amount": {
                      "bsonType": "decimal",
                      "minimum": {
                        "$numberDecimal": "0"
                      }
                    }
                  },
                  "additionalProperties": false
                },
                "minItems": 1,
                "maxItems": 20,
                "uniqueItems": false
              },
              "subtotal_amount": {
                "bsonType": "decimal",
                "minimum": {
                  "$numberDecimal": "0"
                }
              },
              "discount_amount": {
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
              "shipping_address": {
                "bsonType": "null"
              },
              "paid_at": {
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
                "$and": [
                  {
                    "$lte": [
                      "$subtotal_amount",
                      {
                        "$numberDecimal": "1.000000000000000000000000000000000E+6144"
                      }
                    ]
                  },
                  {
                    "$eq": [
                      "$subtotal_amount",
                      {
                        "$round": [
                          "$subtotal_amount",
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
                        "$numberDecimal": "1.000000000000000000000000000000000E+6144"
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
            },
            {
              "$expr": {
                "$and": [
                  {
                    "$lte": [
                      "$shipping_fee",
                      {
                        "$numberDecimal": "1.000000000000000000000000000000000E+6144"
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
                        "$numberDecimal": "1.000000000000000000000000000000000E+6144"
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
                "$lte": [
                  "$discount_amount",
                  "$subtotal_amount"
                ]
              }
            },
            {
              "$expr": {
                "$eq": [
                  "$shipping_fee",
                  {
                    "$numberDecimal": "0"
                  }
                ]
              }
            },
            {
              "$expr": {
                "$eq": [
                  "$subtotal_amount",
                  {
                    "$sum": "$items.subtotal_amount"
                  }
                ]
              }
            },
            {
              "$expr": {
                "$eq": [
                  "$total_amount",
                  {
                    "$add": [
                      {
                        "$subtract": [
                          "$subtotal_amount",
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
                "$allElementsTrue": [
                  {
                    "$map": {
                      "input": "$items",
                      "as": "i",
                      "in": {
                        "$and": [
                          {
                            "$and": [
                              {
                                "$lte": [
                                  "$$i.unit_price",
                                  {
                                    "$numberDecimal": "1.000000000000000000000000000000000E+6144"
                                  }
                                ]
                              },
                              {
                                "$eq": [
                                  "$$i.unit_price",
                                  {
                                    "$round": [
                                      "$$i.unit_price",
                                      2
                                    ]
                                  }
                                ]
                              }
                            ]
                          },
                          {
                            "$eq": [
                              "$$i.subtotal_amount",
                              {
                                "$multiply": [
                                  "$$i.unit_price",
                                  "$$i.quantity"
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
            },
            {
              "$expr": {
                "$or": [
                  {
                    "$ne": [
                      "$payment_status",
                      "paid"
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
            "created_at": -1
          },
          "name": "idx_orders_user_id_created_at"
        },
        {
          "v": 2,
          "key": {
            "is_demo": 1,
            "payment_status": 1,
            "created_at": -1
          },
          "name": "idx_orders_is_demo_payment_status_created_at"
        },
        {
          "v": 2,
          "key": {
            "status": 1,
            "created_at": -1
          },
          "name": "idx_orders_status_created_at"
        }
      ]
    },
    {
      "collection": "user_events",
      "count": 0,
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
      "count": 2,
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
              "created_at"
            ],
            "properties": {
              "_id": {
                "bsonType": "objectId"
              },
              "schema_version": {
                "bsonType": "int",
                "enum": [
                  3
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
        }
      ]
    }
  ]
}
```
