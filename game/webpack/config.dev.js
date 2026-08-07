const path = require("path");
const webpack = require("webpack");
const HtmlWebpackPlugin = require("html-webpack-plugin");

module.exports = {
  mode: "development",
  entry: "./src/main.js",
  output: { path: path.resolve(__dirname, "../dist"), filename: "bundle.js" },
  devServer: { port: 3001, host: "0.0.0.0", historyApiFallback: true, hot: false },
  module: {
    rules: [{ test: /\.js$/, exclude: /node_modules/, loader: "babel-loader" }],
  },
  plugins: [
    new HtmlWebpackPlugin({ template: "./index.html" }),
    new webpack.ProvidePlugin({ Phaser: "phaser" }),
  ],
};
