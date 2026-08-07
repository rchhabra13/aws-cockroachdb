const path = require("path");
const webpack = require("webpack");
const HtmlWebpackPlugin = require("html-webpack-plugin");
const TerserPlugin = require("terser-webpack-plugin");

module.exports = {
  mode: "production",
  entry: "./src/main.js",
  output: {
    path: path.resolve(__dirname, "../dist"),
    filename: "bundle.[contenthash].js",
    clean: true,
  },
  module: {
    rules: [{ test: /\.js$/, exclude: /node_modules/, loader: "babel-loader" }],
  },
  optimization: { minimizer: [new TerserPlugin({ terserOptions: { output: { comments: false } } })] },
  plugins: [
    new HtmlWebpackPlugin({ template: "./index.html" }),
    new webpack.ProvidePlugin({ Phaser: "phaser" }),
  ],
};
