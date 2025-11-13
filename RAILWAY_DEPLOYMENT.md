# Railway Deployment Guide

This guide explains how to deploy the MA Strategy backtesting framework to Railway.

## Prerequisites

1. Railway account ([signup here](https://railway.app))
2. Alpha Vantage API key ([get free key](https://www.alphavantage.co/support/#api-key))

## Deployment Steps

### 1. Environment Variables

Set the following environment variable in your Railway project:

```
ALPHA_VANTAGE_API_KEY=your_api_key_here
```

### 2. Deploy to Railway

#### Option A: Deploy from GitHub

1. Push your code to GitHub
2. Connect your Railway project to the GitHub repository
3. Railway will automatically detect the configuration and build

#### Option B: Deploy using Railway CLI

```bash
# Install Railway CLI
npm i -g @railway/cli

# Login
railway login

# Initialize project
railway init

# Set environment variable
railway variables set ALPHA_VANTAGE_API_KEY=your_api_key_here

# Deploy
railway up
```

## Configuration Files

The following files configure the Railway deployment:

- **`railway.json`**: Main Railway configuration
- **`nixpacks.toml`**: Nixpacks build configuration
- **`Procfile`**: Process type definitions
- **`runtime.txt`**: Python version specification
- **`setup.py`**: Package installation configuration
- **`requirements.txt`**: Python dependencies

## Customizing the Deployment

### Change Symbol or Timeframe

Edit the start command in `railway.json`:

```json
{
  "deploy": {
    "startCommand": "python -m ma_strategy config_example.yaml SPY --alpha-vantage weekly"
  }
}
```

### Use CSV Data Instead

1. Upload your CSV file to Railway
2. Update the start command:

```json
{
  "deploy": {
    "startCommand": "python -m ma_strategy config_example.yaml /path/to/data.csv SYMBOL"
  }
}
```

### Modify Strategy Configuration

Edit `config_example.yaml` or create a new config file and reference it in the start command.

## Troubleshooting

### Build Plan Error

If you encounter "Error creating build plan with Railpack":

1. Ensure all configuration files are present
2. Verify `requirements.txt` is valid
3. Check that Python version in `runtime.txt` is supported

### Runtime Errors

1. Check Railway logs for detailed error messages
2. Verify environment variables are set correctly
3. Ensure sufficient RAM/CPU resources

### API Rate Limits

Alpha Vantage free tier limits:
- 5 API calls per minute
- 500 API calls per day

Consider upgrading if you hit these limits.

## Running as a Scheduled Job

To run the backtest on a schedule:

1. Change the deployment type to "Cron" in Railway
2. Set the schedule (e.g., `0 9 * * *` for daily at 9 AM)
3. Railway will run the command on the specified schedule

## Monitoring

View logs in Railway dashboard:
- Build logs: Shows pip installation and setup
- Deploy logs: Shows backtest execution and results

## Support

For issues specific to:
- **Railway deployment**: [Railway Discord](https://discord.gg/railway)
- **Strategy configuration**: Check `support_ma_backtest_spec_full.md`
- **Alpha Vantage API**: [Alpha Vantage Support](https://www.alphavantage.co/support/)
