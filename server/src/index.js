import app from './app.js';
import serverConfig from './config/serverConfig.js';
// import connectDb from './config/db.js';

const startServer = async () => {
  try {
    app.listen(serverConfig.PORT, () => {
      console.log('Server is running at', serverConfig.PORT);
    });
  } catch (err) {
    console.log(err);
  }
};

startServer();
