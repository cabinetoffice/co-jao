const path = require('path');
const BundleTracker = require('webpack-bundle-tracker');
const MiniCssExtractPlugin = require('mini-css-extract-plugin');
const webpack = require('webpack');

const mode = (process.env.ENV === 'dev' || process.env.ENV === 'ci') ? 'development' : 'production';

module.exports = {
  context: path.resolve(__dirname, 'src'),
  entry: {
    base: './jao_backend/common/static/common/js/base.js',
  },
  output: {
    path: path.resolve(__dirname, 'src/webpack_bundles/'),
    filename: '[name].js',
    publicPath: '/static/webpack_bundles/',
    libraryTarget: 'umd',
    umdNamedDefine: true,
    library: '[name]',
    clean: true,
  },
  devtool: 'source-map',
  module: {
    rules: [
      {
        test: /\.js$/,
        exclude: /node_modules/,
        use: {
          loader: 'babel-loader',
          options: {
            presets: ['@babel/preset-env'],
          },
        },
      },
      {
        test: /\.scss$/,
        use: [
          MiniCssExtractPlugin.loader,
          'css-loader',
          'sass-loader',
        ],
      },
        /*
      {
        test: /\.css$/,
        include: [
          path.resolve(__dirname, 'node_modules/leaflet/dist')
        ],
        use: [
          MiniCssExtractPlugin.loader,
          'css-loader',
        ],
      },
         */
      {
        // Load images and fonts from govuk-frontend to /govuk/assets/
        test: /\.(png|jpg|gif|svg|eot|ttf|woff|woff2|ico)$/,
        loader: 'file-loader',
        options: {
          name: '[path][name].[ext]', // Not hashed (django will handle this)
          context: path.resolve(__dirname, 'node_modules/govuk-frontend/dist/govuk/assets/'),
          outputPath: 'govuk/assets',
          publicPath: '/static/webpack_bundles/govuk/assets/',
        },
      },
    ],
  },
  plugins: [
    new BundleTracker({ path: path.resolve("src"), filename: 'webpack-stats.json' }),
    new MiniCssExtractPlugin({
      filename: '[name].css',
    }),
    // new webpack.ProvidePlugin({
    //   createApplicantMap: ['./src/common/static/common/js/applicant_map.js', 'createApplicantMap'],
    // }),
  ],
  resolve: {
    modules: ["node_modules"],
    extensions: [".js", ".scss"],
  },
};
