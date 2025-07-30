# filters/initial_checks.py

import datetime
from config import INITIAL_FILTERS
from utils.bitquery_api import call_bitquery_api

# ✅ WORKING Bitquery query for new Pump.Fun tokens
BITQUERY_NEW_PUMPFUN_TOKENS_QUERY = """
query NewPumpFunTokens {
  Solana(network: solana) {
    Instructions(
      limit: {count: 50}
      orderBy: {descending: Block_Time}
      where: {
        Instruction: {
          Program: {
            Name: {is: "pump"}
            Method: {is: "create"}
          }
        }
        Block: {
          Time: {since: "2024-12-20T10:00:00Z"}
        }
      }
    ) {
      Block {
        Time
      }
      Transaction {
        Signer
        Signature
      }
      Instruction {
        Accounts {
          Address
        }
        Program {
          Arguments {
            Name
            Value {
              ... on Solana_ABI_Json_Value_Arg {
                json
              }
              ... on Solana_ABI_String_Value_Arg {
                string
              }
            }
          }
        }
      }
    }
  }
}
"""

async def fetch_new_tokens():
    """Fetch new Pump.Fun tokens using correct Bitquery API"""
    try:
        print("🔍 Querying Bitquery for new Pump.Fun tokens...")
        
        # ✅ Make sure this is awaited if call_bitquery_api is async
        result = await call_bitquery_api(BITQUERY_NEW_PUMPFUN_TOKENS_QUERY)
        
        # ✅ Proper error checking
        if not result:
            print("[ERROR] Bitquery returned None response")
            return []
            
        if "data" not in result:
            print(f"[ERROR] Invalid Bitquery response: {result}")
            return []
            
        if "Solana" not in result["data"]:
            print(f"[ERROR] No 'Solana' field in response: {result['data']}")
            return []
            
        if "Instructions" not in result["data"]["Solana"]:
            print(f"[ERROR] No 'Instructions' field in response: {result['data']['Solana']}")
            return []

        instructions = result["data"]["Solana"]["Instructions"]
        print(f"✅ Found {len(instructions)} token creation instructions")
        
        new_tokens = []

        for instruction in instructions:
            try:
                # Extract token mint address (first account is usually the mint)
                accounts = instruction.get("Instruction", {}).get("Accounts", [])
                if not accounts:
                    continue
                    
                mint_address = accounts[0].get("Address")
                if not mint_address:
                    continue

                # Extract token metadata from arguments
                args = instruction.get("Instruction", {}).get("Program", {}).get("Arguments", [])
                name = "Unnamed"
                symbol = ""
                
                for arg in args:
                    if arg.get("Name") == "name":
                        value = arg.get("Value", {})
                        if "string" in value:
                            name = value["string"]
                        elif "json" in value:
                            name = str(value["json"])
                    elif arg.get("Name") == "symbol":
                        value = arg.get("Value", {})
                        if "string" in value:
                            symbol = value["string"]
                        elif "json" in value:
                            symbol = str(value["json"])

                new_tokens.append({
                    "mint": mint_address,
                    "name": name,
                    "symbol": symbol,
                    "created_at": instruction.get("Block", {}).get("Time"),
                    "deployer": instruction.get("Transaction", {}).get("Signer"),
                    "supply": 1000000000,  # Standard Pump.Fun supply
                    # Placeholders for compatibility
                    "marketCap": 0,
                    "holderCount": 0,
                    "volume24h": 0,
                    "devHoldingPercent": 0,
                    "buyCount24h": 0,
                    "socials": [],
                })

            except Exception as e:
                print(f"[WARN] Failed to parse instruction: {e}")
                continue

        print(f"✅ Parsed {len(new_tokens)} new Pump.Fun tokens")
        return new_tokens

    except Exception as e:
        print(f"[ERROR] Bitquery fetch failed: {e}")
        return []

def apply_filters(token):
    """Apply initial filters to tokens"""
    try:
        market_cap = token.get("marketCap", 0)
        holders = token.get("holderCount", 0)
        volume = token.get("volume24h", 0)
        dev_percent = token.get("devHoldingPercent", 100)
        buys = token.get("buyCount24h", 0)
        socials = token.get("socials", [])

        if market_cap < INITIAL_FILTERS["min_marketcap"]:
            return False
        if holders < INITIAL_FILTERS["min_holders"]:
            return False
        if volume < INITIAL_FILTERS["min_volume"]:
            return False
        if dev_percent > INITIAL_FILTERS["max_dev_holding"]:
            return False
        if buys < INITIAL_FILTERS["min_buys"]:
            return False
        if len(socials) < INITIAL_FILTERS["min_socials"]:
            return False

        return True
    except Exception as e:
        print(f"[ERROR] Filtering token failed: {e}")
        return False

async def check_new_tokens():
    """Main function to check new tokens"""
    raw_tokens = await fetch_new_tokens()
    filtered_tokens = [t for t in raw_tokens if apply_filters(t)]
    print(f"[INFO] New Tokens Passed Initial Filters: {len(filtered_tokens)}")
    return filtered_tokens
