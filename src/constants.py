from enum import IntEnum

class SignupType(IntEnum):
    Unknown = 0     # 未知
    ATTENDING = 1   # 参加
    PENDING = 2     # 待定
    ABSENT = 3      # 缺席