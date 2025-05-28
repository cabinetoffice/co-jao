from enum import Enum

from .helpers import SerializableEnumMixin


class GeneralAdviceOptions(Enum, SerializableEnumMixin):
    MORE_APPLICANTS = "I want more applicants"
    QUALITY_APPLICANTS = "I want better quality applicants"
    GENDER_BALANCE = "I want a better gender balance"
    EXTERNAL_BALANCE = "I want more external applicants"
    DISABILITY_BALANCE = "I want more disabled applicants"

    @classmethod
    def get_filter(cls, value, **kwargs):
        if value == cls.MORE_APPLICANTS:
            predicate = {
                "filter": {"range": {"metadata.total apps": {"gte": 20, "lte": 1000}}}
            }
        elif value == cls.QUALITY_APPLICANTS:
            predicate = [
                {
                    "range": {
                        "metadata.% passed sift": {
                            "gte": 50,
                            "lte": 100,
                        }
                    }
                },
                {
                    "range": {
                        "metadata.total apps": {
                            "gte": 50,
                            "lte": 100000,
                        }
                    }
                },
            ]
        elif value == cls.GENDER_BALANCE:
            median_female_applicants = kwargs["median_female_applicants"]
            predicate = [
                {
                    "range": {
                        "metadata.gender_name_Female": {
                            "gte": median_female_applicants,
                            "lte": 100,
                        }
                    }
                },
                {
                    "range": {
                        "metadata.total apps": {
                            "gte": 50,
                            "lte": 100000,
                        }
                    }
                },
            ]
        elif value == cls.EXTERNAL_BALANCE:
            predicate = [
                {
                    "range": {
                        "metadata.approach_name_External": {
                            "gte": 50,
                            "lte": 100,
                        }
                    }
                },
                {
                    "range": {
                        "metadata.total apps": {
                            "gte": 50,
                            "lte": 100000,
                        }
                    }
                },
            ]
        elif value == cls.DISABILITY_BALANCE:
            predicate = [
                {
                    "range": {
                        "metadata.disability_name_Disabled": {
                            "gte": 50,
                            "lte": 100,
                        }
                    }
                },
                {
                    "range": {
                        "metadata.total apps": {
                            "gte": 10,
                            "lte": 100000,
                        }
                    }
                },
            ]
        else:
            raise ValueError(f"Unknown value: {value}")

        return [{"filter": {"bool": {"filter": predicate}}}]


class SkillsAdviceOptions(Enum, SerializableEnumMixin):
    # TODO
    @staticmethod
    def get_filters(value, **kwargs):
        return []


ADVICE_OPTIONS = [
    GeneralAdviceOptions,
    SkillsAdviceOptions,
]


def get_advice_filter(**kwargs):
    pass


# ADVICE_OPTIONS = {
#     "APPLICANTS": {
#         "text": "I want more applicants",
#         "filter": {
#             "bool": {
#                 "filter": {
#                     "range": {"metadata.total apps": {"gte": 20, "lte": 1000}}
#                 }
#             }
#         },
#         "QUALITY_APPLICANTS": {
#             "text": "I want better quality applicants",
#             "filter": {
#                 "bool": {
#                     "filter": [
#                         {
#                             "range": {
#                                 "metadata.% passed sift": {
#                                     "gte": 50,
#                                     "lte": 100,
#                                 }
#                             }
#                         },
#                         {
#                             "range": {
#                                 "metadata.total apps": {
#                                     "gte": 50,
#                                     "lte": 100000,
#                                 }
#                             }
#                         },
#                     ]
#                 }
#             },
#             "EXTERNAL_BALANCE": {
#                 "text": "I want more external applicants",
#                 "filter": {
#                     "bool": {
#                         "filter": [
#                             {
#                                 "range": {
#                                     "metadata.approach_name_External": {
#                                         "gte": 50,
#                                         "lte": 100,
#                                     }
#                                 }
#                             },
#                             {
#                                 "range": {
#                                     "metadata.total apps": {
#                                         "gte": 50,
#                                         "lte": 100000,
#                                     }
#                                 }
#                             },
#                         ]
#                     }
#                 },
#                 "GENDER_BALANCE": {
#                     "text": "I want a better gender balance",
#                     "filter": {
#                         "bool": {
#                             "filter": [
#                                 {
#                                     "range": {
#                                         "metadata.gender_name_Female": {
#                                             "gte": median_female_applicants,
#                                             "lte": 100,
#                                         }
#                                     }
#                                 },
#                                 {
#                                     "range": {
#                                         "metadata.total apps": {
#                                             "gte": 50,
#                                             "lte": 100000,
#                                         }
#                                     }
#                                 },
#                             ]
#                         }
#                     },
#                     "DISABILITY_BALANCE": {
#                         "text": "I want more disabled applicants",
#                         "filter": {
#                             "bool": {
#                                 "filter": [
#                                     {
#                                         "range": {
#                                             "metadata.disability_name_Disabled": {
#                                                 "gte": 50,
#                                                 "lte": 100,
#                                             }
#                                         }
#                                     },
#                                     {
#                                         "range": {
#                                             "metadata.total apps": {
#                                                 "gte": 10,
#                                                 "lte": 100000,
#                                             }
#                                         }
#                                     },
#                                 ]
#                             }
#                         },
#                     },
#                 },
#             },
#         },
#     }
# }


def get_advice_filters(advice_category, advice_type, median_female_applicants):
    ADVICE_FILTERS = {
        "APPLICANTS": {
            "text": "I want more applicants",
            "filter": {
                "bool": {
                    "filter": {
                        "range": {"metadata.total apps": {"gte": 20, "lte": 1000}}
                    }
                }
            },
            "QUALITY_APPLICANTS": {
                "text": "I want better quality applicants",
                "filter": {
                    "bool": {
                        "filter": [
                            {
                                "range": {
                                    "metadata.% passed sift": {
                                        "gte": 50,
                                        "lte": 100,
                                    }
                                }
                            },
                            {
                                "range": {
                                    "metadata.total apps": {
                                        "gte": 50,
                                        "lte": 100000,
                                    }
                                }
                            },
                        ]
                    }
                },
                "EXTERNAL_BALANCE": {
                    "text": "I want more external applicants",
                    "filter": {
                        "bool": {
                            "filter": [
                                {
                                    "range": {
                                        "metadata.approach_name_External": {
                                            "gte": 50,
                                            "lte": 100,
                                        }
                                    }
                                },
                                {
                                    "range": {
                                        "metadata.total apps": {
                                            "gte": 50,
                                            "lte": 100000,
                                        }
                                    }
                                },
                            ]
                        }
                    },
                    "GENDER_BALANCE": {
                        "text": "I want a better gender balance",
                        "filter": {
                            "bool": {
                                "filter": [
                                    {
                                        "range": {
                                            "metadata.gender_name_Female": {
                                                "gte": median_female_applicants,
                                                "lte": 100,
                                            }
                                        }
                                    },
                                    {
                                        "range": {
                                            "metadata.total apps": {
                                                "gte": 50,
                                                "lte": 100000,
                                            }
                                        }
                                    },
                                ]
                            }
                        },
                        "DISABILITY_BALANCE": {
                            "text": "I want more disabled applicants",
                            "filter": {
                                "bool": {
                                    "filter": [
                                        {
                                            "range": {
                                                "metadata.disability_name_Disabled": {
                                                    "gte": 50,
                                                    "lte": 100,
                                                }
                                            }
                                        },
                                        {
                                            "range": {
                                                "metadata.total apps": {
                                                    "gte": 10,
                                                    "lte": 100000,
                                                }
                                            }
                                        },
                                    ]
                                }
                            },
                        },
                    },
                },
            },
        }
    }
