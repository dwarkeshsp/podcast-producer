import argparse
import assemblyai as aai
import anthropic
import os
import ffmpeg
import json
from pathlib import Path

clip_suggestions_prompt = """
You are writing tweets in the style of top intellectual podcaster, Dwarkesh Patel.

Here's my sense of what makes tweets great:
It's very helpful when you frame a very specific question or motivation or hook that you're going to answer.

Your task: Identify 8 of the most compelling segments to make clips of.

For each clip, provide BOTH:
1. tweet_text - The suggested tweet text that will accompany the video clip
2. exact_transcript - The exact verbatim transcript from the source (word-for-word, so it can be matched against the transcript JSON to find precise timestamps)

Return your response as a JSON array following this EXACT format:

{examples}

CRITICAL: The "exact_transcript" field must contain the EXACT words from the source transcript, word-for-word, including filler words and natural speech patterns, so it can be precisely matched to find timestamps in the JSON.

Now, here is the transcript to analyze:

{transcript}
"""

clip_suggestion_examples = [
    {
        "tweet_text": "I asked Victor Shih this question - why has the Chinese stock market been flat for so long despite the economy growing so fast?\n\nThis puzzle is explained via China's system of financial repression.\n\nIf you save money in China, banks are not giving you the true competitive interest rate. Rather, they'll give you the government capped 1.3% (lower than inflation, meaning you're earning a negative return).\n\nThe net interest (which is basically a tax on all Chinese savers) is shoveled into politically favored state owned enterprises that survive only on subsidized credit.\n\nBut here's what I didn't understand at first: Why don't companies just raise equity capital and operate profitably for shareholders?\n\nThe answer apparently is that there's no 'outside' the system.\n\nThe state doesn't just control credit - it controls land, permits, market access, even board seats through Party committees. Companies that prioritize profits over market share lose these privileges. Those that play along get subsidized loans, regulatory favors, and government contracts.\n\nRegular savers, founders, and investors are all turned into unwitting servants of China's industrial policy.",
        "exact_transcript": "Why is it the case that the Chinese stock market has performed so badly, even though the economy has grown a lot? There is a deep fundamental difference between capitalism and socialism. And it sounds very philosophical, but I think, you know, this might help sort of your Gen Z listeners think about this. Because for socialism, they only care about output. The state can use the state banking system, which they control, to allocate a huge amount of capital to maximize the output of all these different things that they care about. But when you maximize the output, you don't necessarily make money doing that. Whereas capitalism wants to maximize profit. But the companies aren't socialist, right? The companies are profit-seeking. Well, no, but because the financial system is socialist, they're forced into socialist-like behavior. You know, you can't go into a bank and say, look, I make robotics. This robot that I'm going to make is going to be highly profitable, you know, down the road. But I can only make like 10 of them. And then the bank would be like, well, this is BS. You know, the central government has told us to maximize your production. It's a socialist banking system basically says, you know, even if you never make any money or hardly any money, that's okay. As long as the Chinese government tells us that this is a strategic sector, as long as you can prove to us you can actually produce the thing that we want you to produce. If you never ever make money doing that, that's perfectly fine."
    },
    {
        "tweet_text": "AGI timelines are very bimodal. It's either by 2030 or bust.\n\nAI progress over the last decade has been driven by scaling training compute of frontier systems (3.55x a year, 160x over 4 years).\n\nThis simply cannot continue beyond this decade, whether you look at chips, power, even fraction of raw GDP used on training.\n\nAfter 2030, AI progress has to mostly come from algorithmic progress. But even there the low hanging fruit will be plucked (at least under the deep learning paradigm).\n\nSo the yearly probability of AGI craters. And we're plausibly looking at 2040+ timelines.\n\nI discuss this dynamic with @_sholtodouglas and @TrentonBricken.",
        "exact_transcript": "There's another dynamic, which was a reason that Ege and Tame, when they're on the podcast, said that they were pessimistic, is that they think we're further away from solving these problems with long context, coherent agency, advanced multimodality than you think. And then their point is that the progress that's happened in the past over like reasoning or something has required many orders of magnitude increase in compute. And if this scale of compute increase can continue beyond 2030, not just because of chips, but also because of power and like raw GDP even. And because we don't think we get it by 2030 or 2028, the probability per year just goes down a bunch. Yeah, this is like bimodal distribution. A conversation I had with Leopold turned into a section in a situation where it's called This Decade or Bust, which is on exactly this topic. Which is basically that for the next couple of years, we can dramatically increase our training compute. And RL is going to be so exciting this year because we can dramatically increase the amount of compute that we apply to it. And this is also one of the reasons why the gap between like say DeepSeq and O1 was so close at the beginning of the year because they were able to apply like the same amount of compute to the RL process. So that compute differential actually like will sort of be magnified over the course of this year. I mean, bringing it back to the there's so much low hanging fruit. Yeah. It's been wild seeing the efficiency gains that these models have experienced over the last two years. With respect to DeepSeq, I mean, just really hammering home and like Dario has a nice essay on this. DeepSeq was nine months after Claude III's sonnet. And if we retrained the same model today or at the same time as the DeepSeq work, we also could have trained it for 5 million or whatever the advertised amount was. And so what's impressive or surprising is that DeepSeq has gotten to the frontier. But I think there's a common misconception still that they are above and beyond the frontier. And I don't think that's right. I think they just waited and then were able to take advantage of all the efficiency gains that everyone else was also seeing."
    },
    {
        "tweet_text": "I have been obsessed with what the geneticist David Reich told me in our interview together.\n\nThe story of human evolution we're now learning from new evidence is so crazy.\n\n70,000 years ago, half a dozen different species of humans (Neanderthals, Denisovans, 'Hobbits', etc) lived across Eurasia.\n\nAnd then some small group of modern humans (only 1,000 to 10,000 people) drove all of them to extinction.\n\nEveryone native to Eurasia and America is descended from this one tribe.\n\nHere's the crazy part - modern humans with language and big brains have been around for hundreds of thousands of years.\n\nAnd we had ventured out of Africa before. But we were always beat back by these other humans.\n\nWhat did this small group of humans 70,000 years ago figure out such that they completely dominated the planet?\n\nFull episode out Thursday.",
        "exact_transcript": "70,000 years ago, there are half a dozen different human species all around the world. And then this group that's descended from the people in sub-Saharan Africa, initially like 1,000 to 10,000 people, explodes all across the world. Not only do we dominate, but like, in fact, we drive them to extinction. So something seems like it changed. What do you reckon it was? Already, the common ancestors of Neanderthals and modern humans probably had a brain as large as ours. So I'm very sympathetic to the idea that it's hardly genetic. I think that this is cultural innovation. The whole continent of sub-Saharan Africa, and probably Eurasia at this time, is full of tens of thousands of little groups that are communicating hardly at all with each other. In every group of human beings, they accumulate shared cultural knowledge. But if you have a limited-sized group of people that's not interacting with a sufficiently other large group of people, you know, there's a natural disaster, key elders in the group die, and knowledge gets lost, and there's not a critical mass of shared knowledge. But once it goes above some kind of critical mass, the group can get larger, the amount of shared knowledge becomes greater, and then you have a runaway process where an increasing body of shared knowledge of how to make particular tools, how to innovate, language, conceptual ideas run amok. The great majority of them are wiped out. And so what you have is a vast experiment with an archipelago of these groups. And maybe something takes off somewhere, and maybe that's what happens 50 to 100,000 years ago. And people who all have the capacity to do these things."
    },
    {
        "tweet_text": "Japan was richer per capita than the US in the late 1980s.\n\nToday it sits at the bottom among developed countries.\n\nHow does an economic superpower fall this far and never recover?\n\nKenneth Rogoff (former Chief Economist of IMF) walked me through what he believes was a catastrophic mistake.\n\nIn 1985, the US pressured Japan to rapidly strengthen the yen and liberalize its financial markets through the Plaza Accord.\n\nThe yen doubled in value in just 3 years. To offset the economic shock, Japan slashed interest rates and flooded the economy with cheap credit.\n\nJapanese banks, suddenly freed from decades of tight regulation, went on a lending spree. They poured money into real estate and stocks with little risk assessment. Japan's stock market became worth more than the US stock market despite having half the population. The total value of Japanese real estate was 4 times the value of all US real estate.\n\nWhen the bubble burst in 1991, banks were left with massive bad loans. The entire financial system seized up, creating a \"lost decade\" of deflation and stagnation.\n\nHere's what stunned me: Rogoff estimates Japan would be 50% wealthier per person today without this crisis.\n\nI didn't grasp before this interview how devastating financial crises are. They don't just cause a temporary recession - they permanently alter a country's growth trajectory.\n\nThree decades later, Japan still hasn't recovered.\n\nFull interview with @krogoff out tomorrow.",
        "exact_transcript": "So suppose that crisis hadn't happened.(...) How much wealth is Japan today than have other? Oh, I think 50% wealthier, or 50% way wealthier. They were richer than the United States, they were richer than any European country, than Germany, than France, than Italy. They moved to the bottom of the rung. I think we effectively forced them to move faster to open up and deregulate, than culturally and politically they were ready to. there's this thing called the Plaza Accord in September, 1985. where we push them to make their exchange rate more. And I used to say, why did that happen in 1985? we date the crisis in 1992, it's seven years later.(...) And I think I continue to think that. But I would say over the years, and particularly in recent years, I'm thinking I was wrong. These things unfold slowly. Crises don't happen overnight. They deregulated and it worked, but they didn't know what they were doing. And I think this was a huge mistake by Japan to agree. at a 10th anniversary of the Plaza Accord held in Tokyo, was the head of the Bank of Japan, he gave the speech to officials and he went like this and apologized very symbolically. I have ruined our country, I did this, I take responsibility. liberalization needs to be done gradually. If you do it too quickly, you get a crisis. That's many crises caused by that."
    }
]


def get_claude_response(prompt):
    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    response = client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=16000,
            thinking={
                "type": "enabled",
                "budget_tokens": 10000
            },
            messages=[
                {
                    "role": "user",
                    "content": [{"type": "text", "text": prompt}]
                }
            ]
    )

    for block in response.content:
        if block.type == "thinking":
            print("Thinking: ", block.thinking)
        elif block.type == "text":
            print(block.text)
    return response.content[-1].text.strip()

def get_readable_transcript(transcript_data):
    transcript = ""
    current_speaker = ""
    for utt in transcript_data["utterances"]:
        if utt["speaker"] != current_speaker:
            current_speaker = utt["speaker"]
            transcript += f"SPEAKER {current_speaker}:\n"
        transcript += f"{utt['text']}\n"
    return transcript

def suggest_clips(transcript_data):
    readable_transcript = get_readable_transcript(transcript_data)
    examples_json = json.dumps(clip_suggestion_examples, indent=2, ensure_ascii=False)

    full_prompt = clip_suggestions_prompt.format(examples=examples_json, transcript=readable_transcript)
    print(full_prompt)
    response = get_claude_response(full_prompt)
    return response

def turn_clip_sugggestion_into_timestamps(clip_suggestion):
    pass

def render_twitter_clip(timestamps):
    pass

def save_transcript_json(transcript_data: dict, json_path: str):
    with open(json_path, 'w', encoding='utf8') as f:
        json_str = json.dumps(transcript_data, ensure_ascii=False, indent=2)
        f.write(json_str)
    print(f"Saved transcript to {json_path}")

def load_transcript_json(json_path: str) -> dict:
    with open(json_path, 'r') as f:
        return json.load(f)

def transcribe(file_path: str, json_path: str):
    if os.path.exists(json_path):
        print(f"Loading existing transcript from {json_path}")
        return load_transcript_json(json_path)
    
    print(f"Generating new transcript for {file_path}")
    aai.settings.api_key = os.getenv("ASSEMBLYAI_API_KEY")
    config = aai.TranscriptionConfig(
        speaker_labels=True,
        speech_models=['slam-1'],
    )
    aai_transcript = aai.Transcriber().transcribe(file_path, config=config)
    
    transcript_data = aai_transcript.json_response
    save_transcript_json(transcript_data, json_path)
    return transcript_data

def convert_video_to_audio(video_path: str, audio_path: str):
    ffmpeg.input(video_path).output(audio_path, acodec='pcm_s16le', ar='16000').overwrite_output().run(capture_stdout=True, capture_stderr=True)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("ep_path", type=str, help="The path to the full episode")
    args = parser.parse_args()
    
    # Generate transcript JSON path in data/transcripts/
    ep_path = Path(args.ep_path)
    transcripts_dir = Path("data/transcripts")
    transcripts_dir.mkdir(parents=True, exist_ok=True)
    transcript_json_path = transcripts_dir / f"{ep_path.stem}.json"
    
    audio_path = "temp_audio.wav"
    convert_video_to_audio(args.ep_path, audio_path)
    transcript_data = transcribe(audio_path, str(transcript_json_path))

    
    os.remove(audio_path)
    suggest_clips(transcript_data)




if __name__ == "__main__":
    main()
