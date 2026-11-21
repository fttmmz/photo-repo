// Copy this file to config.js and add the Cognito IDs supplied by Member 5.
// Do not commit config.js. The API endpoint and AWS region were supplied by the team.
window.APP_CONFIG = {
  region: "eu-north-1",
  userPoolId: "eu-north-1_kKHYKZdbb",
  clientId: "480opvjmar49egrtrm15fendhj",
  apiBaseUrl: "https://vudt3y9jel.execute-api.eu-north-1.amazonaws.com/prod",
  photoBucket: "photo-repo-photos-678530698612-eu-north-1",
  thumbnailBucket: "photo-repo-thumbs-678530698612-eu-north-1",
  dynamoTable: "photo-repo-photos",
  routes: {
    list: "/photos",
    search: "/photos/search",
    searchParam: "q",
    uploadUrl: "/photos/upload-url",
    get: "/photos/{photoId}",
    remove: "/photos/{photoId}"
  },
  maxFileBytes: 10 * 1024 * 1024
};
