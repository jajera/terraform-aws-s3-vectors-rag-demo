function getPoolData() {
  return {
    UserPoolId: window.APP_CONFIG.userPoolId,
    ClientId: window.APP_CONFIG.clientId,
  };
}

function getUserPool() {
  return new AmazonCognitoIdentity.CognitoUserPool(getPoolData());
}

function getCurrentUser() {
  return getUserPool().getCurrentUser();
}

function getSession() {
  return new Promise((resolve, reject) => {
    const user = getCurrentUser();
    if (!user) {
      reject(new Error("Not signed in"));
      return;
    }
    user.getSession((err, session) => {
      if (err || !session || !session.isValid()) {
        reject(err || new Error("Invalid session"));
        return;
      }
      resolve(session);
    });
  });
}

function getIdToken() {
  return getSession().then((session) => session.getIdToken().getJwtToken());
}

function signIn(email, password) {
  return new Promise((resolve, reject) => {
    const user = new AmazonCognitoIdentity.CognitoUser({
      Username: email,
      Pool: getUserPool(),
    });
    const authDetails = new AmazonCognitoIdentity.AuthenticationDetails({
      Username: email,
      Password: password,
    });
    user.authenticateUser(authDetails, {
      onSuccess: () => resolve(user),
      onFailure: (err) => reject(err),
    });
  });
}

function signOut() {
  const user = getCurrentUser();
  if (user) {
    user.signOut();
  }
}

function isAdmin(session) {
  const payload = session.getIdToken().payload;
  const groups = payload["cognito:groups"];
  if (Array.isArray(groups)) {
    return groups.includes("admins");
  }
  return typeof groups === "string" && groups.split(",").includes("admins");
}
