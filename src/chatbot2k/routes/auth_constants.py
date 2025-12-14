from twitchAPI.type import AuthScope

SCOPES = [AuthScope.USER_READ_MODERATED_CHANNELS]
JWT_ALG = "HS256"
SESSION_COOKIE = "session"
OAUTH_STATE_COOKIE = "twitch_oauth_state"
JWT_EXPIRY_DAYS = 7
